from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QComboBox,
    QPushButton,
    QMessageBox,
    QLabel,
    QLineEdit,
    QSplitter,
    QFrame,
    QFileDialog,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QTextEdit,
    QProgressDialog,
)
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtCore import Qt, QCoreApplication
import logging

# Local imports (ensure package is on PYTHONPATH when running from project root)
from photo_cleaner.db.schema import Database
from photo_cleaner.duplicates.finder import DuplicateFinder
from photo_cleaner.core.duplicate_groups import FileEntry, pick_best_file
from photo_cleaner.ui.thumbnail_cache import get_thumbnail
import uuid
import time
import shutil
from PIL import Image, ExifTags
from photo_cleaner.io.file_scanner import FileScanner
from PySide6.QtWidgets import QFileDialog as _QFileDialog
from PySide6.QtCore import QSize


class CleanupUI(QWidget):
    """Minimal UI to inspect duplicate groups and delete selected removals."""

    def __init__(self, db_path: Path | str = "photo_cleaner.db") -> None:
        super().__init__()
        self.db_path = Path(db_path)
        self.db = Database(self.db_path)
        self.conn = self.db.connect()

        self.setWindowTitle("PhotoCleaner — Cleanup")
        # German title
        self.setWindowTitle(t("photocleaner_aufraeumen"))
        self.resize(900, 600)

        # Main splitter: left = list, right = preview/details
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel
        left = QWidget()
        left_l = QVBoxLayout(left)
        title = QLabel(t("gefundene_gruppen"))
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        left_l.addWidget(title)

        # search
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter: Dateiname, exact, similar...")
        left_l.addWidget(self.search)

        # Sort options
        sort_row = QHBoxLayout()
        sort_label = QLabel("Sortieren:")
        self.sort_box = QComboBox()
        self.sort_box.addItems([
            "Keine Sortierung",
            "Name ↑",
            "Name ↓",
            "Neueste zuerst",
            "Älteste zuerst",
            "Zu entfernende (absteigend)",
        ])
        sort_row.addWidget(sort_label)
        sort_row.addWidget(self.sort_box)
        left_l.addLayout(sort_row)

        # Input folder chooser
        folder_row = QHBoxLayout()
        self.input_folder_edit = QLineEdit()
        self.input_folder_edit.setPlaceholderText("Quellordner auswählen...")
        self.choose_folder_btn = QPushButton(t("select_folders"))
        folder_row.addWidget(self.input_folder_edit)
        folder_row.addWidget(self.choose_folder_btn)
        left_l.addLayout(folder_row)

        # Organize button
        self.organize_btn = QPushButton(t("bilder_sortieren_jmt"))
        # Target folder chooser + dry-run
        target_row = QHBoxLayout()
        self.target_folder_edit = QLineEdit()
        self.target_folder_edit.setPlaceholderText("Zielordner (optional)")
        self.choose_target_btn = QPushButton(t("ziel_waehlen"))
        target_row.addWidget(self.target_folder_edit)
        target_row.addWidget(self.choose_target_btn)
        left_l.addLayout(target_row)

        self.dryrun_checkbox = QCheckBox("Nur Vorschau (Dry‑Run)")
        self.dryrun_checkbox.setChecked(True)
        left_l.addWidget(self.dryrun_checkbox)
        left_l.addWidget(self.organize_btn)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        left_l.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton("Aktualisieren")
        self.delete_btn = QPushButton(t("loesche_ausgewaehlte"))
        self.undo_btn = QPushButton("Papierkorb: Wiederherstellen")
        self.delete_btn.setEnabled(False)
        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.undo_btn)
        btn_row.addWidget(self.delete_btn)
        left_l.addLayout(btn_row)

        splitter.addWidget(left)

        # Right panel (preview + details)
        right = QWidget()
        right_l = QVBoxLayout(right)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedHeight(360)
        right_l.addWidget(self.preview)

        self.meta_label = QLabel(t("waehle_eine_gruppe_um_details_zu_sehen"))
        self.meta_label.setWordWrap(True)
        right_l.addWidget(self.meta_label)

        # Trash list (deleted files)
        trash_title = QLabel("Papierkorb")
        trash_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        right_l.addWidget(trash_title)
        self.trash_list = QListWidget()
        self.trash_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.trash_list.setFixedHeight(160)
        right_l.addWidget(self.trash_list)

        trash_row = QHBoxLayout()
        self.restore_selected_btn = QPushButton("Wiederherstellen")
        self.perm_delete_btn = QPushButton(t("endgueltig_loeschen"))
        self.restore_selected_btn.setEnabled(False)
        self.perm_delete_btn.setEnabled(False)
        trash_row.addWidget(self.restore_selected_btn)
        trash_row.addWidget(self.perm_delete_btn)
        right_l.addLayout(trash_row)

        action_row = QHBoxLayout()
        self.keep_btn = QPushButton(t("als_behalten_markieren"))
        self.remove_btn = QPushButton(t("dateien_entfernen"))
        self.keep_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        action_row.addWidget(self.keep_btn)
        action_row.addWidget(self.remove_btn)
        right_l.addLayout(action_row)

        splitter.addWidget(right)

        splitter.setSizes([320, 580])
        main_layout.addWidget(splitter)

        # Wire events
        self.refresh_btn.clicked.connect(self.load_groups)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.remove_btn.clicked.connect(self.delete_selected)
        self.keep_btn.clicked.connect(self._mark_keep)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.search.textChanged.connect(self._apply_filter)
        self.sort_box.currentIndexChanged.connect(self._on_sort_changed)
        self.undo_btn.clicked.connect(self._undo_last_delete)
        self.trash_list.itemSelectionChanged.connect(self._on_trash_selection_changed)
        self.restore_selected_btn.clicked.connect(self._restore_selected)
        self.perm_delete_btn.clicked.connect(self._perm_delete_selected)
        self.choose_folder_btn.clicked.connect(self._choose_input_folder)
        self.organize_btn.clicked.connect(self._organize_folder)
        self.choose_target_btn.clicked.connect(self._choose_target_folder)

        self.groups: List[dict] = []
        self._current_filter = ""
        self.load_groups()

    def _on_sort_changed(self, *_args) -> None:
        # Re-apply sorting and refresh list display
        self._sort_groups()
        self._apply_filter(self._current_filter)

    def _sort_groups(self) -> None:
        key = self.sort_box.currentText()
        if key == "Keine Sortierung":
            return
        if key == "Name ↑":
            self.groups.sort(key=lambda g: str(g.get("keep") or "").lower())
        elif key == "Name ↓":
            self.groups.sort(key=lambda g: str(g.get("keep") or "").lower(), reverse=True)
        elif key == "Neueste zuerst":
            def _ctime(g):
                k = g.get("keep")
                try:
                    return Path(k).stat().st_ctime
                except OSError:
                    logger.debug(f"Failed to stat {Path(k).name}", exc_info=True)
                    return 0
            self.groups.sort(key=_ctime, reverse=True)
        elif key == "Älteste zuerst":
            def _ctime2(g):
                k = g.get("keep")
                try:
                    return Path(k).stat().st_ctime
                except OSError:
                    logger.debug(f"Failed to stat {Path(k).name}", exc_info=True)
                    return 0
            self.groups.sort(key=_ctime2)
        elif key == "Zu entfernende (absteigend)":
            self.groups.sort(key=lambda g: len(g.get("remove") or []), reverse=True)

    def _choose_input_folder(self) -> None:
        d = _QFileDialog.getExistingDirectory(self, "Quellordner wählen", str(Path('.').resolve()))
        if d:
            self.input_folder_edit.setText(d)

    def _choose_target_folder(self) -> None:
        d = _QFileDialog.getExistingDirectory(self, "Zielordner wählen (optional)", str(Path('.').resolve()))
        if d:
            self.target_folder_edit.setText(d)

    def _get_exif_date(self, path: Path):
        try:
            with Image.open(path) as im:
                exif = im._getexif()
                if not exif:
                    return None
                # Map tag names
                for tag, val in exif.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    if decoded in ("DateTimeOriginal", "DateTime"):
                        return val
        except (OSError, AttributeError, TypeError):
            logger.debug(f"Failed to extract EXIF from {path.name}", exc_info=True)
            return None

    def _parse_exif_datetime(self, dt_str: str):
        # EXIF DateTime format: 'YYYY:MM:DD HH:MM:SS'
        try:
            parts = dt_str.split()
            date = parts[0]
            y,m,d = date.split(":")
            return int(y), int(m), int(d)
        except (ValueError, IndexError):
            logger.debug(f"Failed to parse EXIF datetime: {dt_str}", exc_info=True)
            return None

    def _organize_folder(self) -> None:
        src = self.input_folder_edit.text().strip()
        if not src:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst einen Quellordner auswählen.")
            return
        srcp = Path(src)
        if not srcp.exists() or not srcp.is_dir():
            QMessageBox.warning(self, "Fehler", "Ungültiger Quellordner.")
            return

        # destination root: explicit target if set, otherwise '<source>_organized'
        target_text = self.target_folder_edit.text().strip()
        if target_text:
            dest_root = Path(target_text)
        else:
            dest_root = srcp.parent / (srcp.name + "_organized")
        dest_root.mkdir(parents=True, exist_ok=True)

        dry_run = bool(self.dryrun_checkbox.isChecked())

        scanner = FileScanner(srcp)
        moved = 0
        errors = 0
        error_msgs = []
        cursor = self.conn.cursor()
        logger = logging.getLogger(__name__)

        # build planned moves first with progress
        planned = []
        progress = QProgressDialog("Scanne Dateien...", "Abbrechen", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(500)
        
        file_list = list(scanner.scan())
        total = len(file_list)
        progress.setMaximum(total)
        
        for idx, p in enumerate(file_list):
            if progress.wasCanceled():
                break
            progress.setValue(idx)
            progress.setLabelText(f"Plane Verschiebung {idx+1}/{total}...")
            QCoreApplication.processEvents()
            
            try:
                exif_dt = self._get_exif_date(p)
                ymd = None
                if exif_dt:
                    parsed = self._parse_exif_datetime(exif_dt)
                    if parsed:
                        ymd = parsed
                if not ymd:
                    st = p.stat()
                    from datetime import datetime

                    dt = datetime.fromtimestamp(st.st_mtime)
                    ymd = (dt.year, dt.month, dt.day)

                year, month, day = ymd
                dest_dir = dest_root / f"{year:04d}" / f"{month:02d}" / f"{day:02d}"
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / p.name
                if dest.exists():
                    base = dest.stem
                    suffix = dest.suffix
                    i = 1
                    while True:
                        candidate = dest_dir / f"{base}_{i}{suffix}"
                        if not candidate.exists():
                            dest = candidate
                            break
                        i += 1
                planned.append((str(p), str(dest)))
            except Exception as e:
                errors += 1
                error_msgs.append(f"{p.name}: {str(e)}")
                logger.error(f"Error planning {p}: {e}")
        
        progress.setValue(total)

        # If dry_run, just report counts
        if dry_run:
            QMessageBox.information(self, "Vorschau", f"Dry‑Run: {len(planned)} Dateien geplant, {errors} Fehler beim Planen.")
            return

        # Show preview dialog and ask for confirmation (unless auto-confirm)
        do_confirm = True
        if getattr(self, '_auto_confirm', False):
            do_confirm = True
        else:
            dlg = PlanDialog(self, planned)
            res = dlg.exec()
            do_confirm = res == QDialog.Accepted

        if not do_confirm:
            QMessageBox.information(self, "Abgebrochen", "Organisieren abgebrochen.")
            return

        # perform moves with progress
        progress2 = QProgressDialog("Verschiebe Dateien...", "Abbrechen", 0, len(planned), self)
        progress2.setWindowModality(Qt.WindowModal)
        progress2.setMinimumDuration(500)
        
        for idx, (src_path, dst_path) in enumerate(planned):
            if progress2.wasCanceled():
                break
            progress2.setValue(idx)
            progress2.setLabelText(f"Verschiebe {idx+1}/{len(planned)}...")
            QCoreApplication.processEvents()
            
            try:
                p = Path(src_path)
                dest = Path(dst_path)
                shutil.move(str(p), str(dest))
                try:
                    cursor.execute("UPDATE files SET path = ? WHERE path = ?", (str(dest), str(p)))
                except Exception as e:
                    logger.warning(f"DB update failed for {p}: {e}")
                moved += 1
            except Exception as e:
                errors += 1
                error_msgs.append(f"{Path(src_path).name}: {str(e)}")
                logger.error(f"Move failed {src_path} -> {dst_path}: {e}")
        
        progress2.setValue(len(planned))

        if not dry_run:
            self.conn.commit()

        msg = f"Organisieren abgeschlossen: {moved} verschoben, {errors} Fehler."
        if error_msgs and len(error_msgs) <= 10:
            msg += "\n\nFehler:\n" + "\n".join(error_msgs[:10])
        elif error_msgs:
            msg += f"\n\n{len(error_msgs)} Fehler aufgetreten (siehe Log)."
        QMessageBox.information(self, "Fertig", msg)
        # reload groups and trash view
        self.load_groups()
        self._load_trash()

    def on_selection_changed(self, idx: int) -> None:
        self.delete_btn.setEnabled(idx >= 0)

    def load_groups(self) -> None:
        """Load duplicate groups from DB and display them."""
        self.list_widget.clear()
        self.groups.clear()

        finder = DuplicateFinder(self.db)

        # Exact groups
        exact = finder.find_exact_duplicates()
        cursor = self.conn.cursor()
        for row in exact:
            file_hash = row[0]
            cursor.execute("SELECT path, created_time, is_keeper FROM files WHERE file_hash = ?", (file_hash,))
            rows = cursor.fetchall()
            entries: List[FileEntry] = []
            for r in rows:
                p = Path(r[0])
                created = r[1] if r[1] is not None else 0
                is_keeper = bool(r[2]) if len(r) > 2 else False
                entries.append(FileEntry(path=p, width=0, height=0, created=created, name=p.name))

            # If any file in the group was previously marked as keeper, prefer it
            keeper_override = None
            for r in rows:
                try:
                    if len(r) > 2 and bool(r[2]):
                        keeper_override = Path(r[0])
                       (IndexError, TypeError):
                    logger.debug("Failed to check keeper flag", exc_info=True)xception:
                    pass

            if len(entries) <= 1:
                continue

            if keeper_override:
                best = next((e for e in entries if e.path == keeper_override), pick_best_file(entries))
            else:
                best = pick_best_file(entries)
            to_remove = [e.path for e in entries if e.path != best.path]
            title = f"Exact: keep={best.path.name} remove={len(to_remove)}"
            self.groups.append({"keep": best.path, "remove": to_remove, "title": title})
            item = QListWidgetItem(title)
            try:
                if best.path.exists():
                    t = get_thumbnail(best.path, (64, 64))
                    pix = QPixmap(str(t))
                    item.setIcon(QIcon(pix))
            except (OSError, TypeError, RuntimeError):
                logger.debug(f"Failed to create thumbnail for exact match", exc_info=True)
            self.list_widget.addItem(item)

        # Similar pairs (pairwise)
        similar = finder.find_similar_duplicates()
        seen = set()
        for p1, p2, dist in similar:
            key = tuple(sorted((p1, p2)))
            if key in seen:
                continue
            seen.add(key)
            # Check keeper flag for similar pair from files table when possible
            cursor = self.conn.cursor()
            cursor.execute("SELECT is_keeper FROM files WHERE path = ?", (p1,))
            r1 = cursor.fetchone()
            is_k1 = bool(r1[0]) if r1 and len(r1) > 0 else False
            cursor.execute("SELECT is_keeper FROM files WHERE path = ?", (p2,))
            r2 = cursor.fetchone()
            is_k2 = bool(r2[0]) if r2 and len(r2) > 0 else False

            e1 = FileEntry(path=Path(p1), width=0, height=0, created=0, name=Path(p1).name)
            e2 = FileEntry(path=Path(p2), width=0, height=0, created=0, name=Path(p2).name)
            # reuse existing grouping heuristic
            group = [e1, e2]
            # Respect keeper flags if present
            if is_k1:
                best = e1
            elif is_k2:
                best = e2
            else:
                best = pick_best_file(group)
            to_remove = [e.path for e in group if e.path != best.path]
            title = f"Similar (d={dist}): keep={best.path.name} remove={len(to_remove)}"
            self.groups.append({"keep": best.path, "remove": to_remove, "title": title})
            item = QListWidgetItem(title)
            try:
                if best.path.exists():
                    t = get_thumbnail(best.path, (64, 64))
                    pix = QPixmap(str(t))
                    item.setIcon(QIcon(pix))
            except (OSError, TypeError, RuntimeError):
                logger.debug(f"Failed to create thumbnail for similar match", exc_info=True)
            self.list_widget.addItem(item)

        if not self.groups:
            self.list_widget.addItem("(No duplicate groups found)")

    def delete_selected(self) -> None:
        selected = self.list_widget.selectedIndexes()
        if not selected:
            return

        # aggregate all removal paths from selected groups
        remove_paths = []
        for idx in set(i.row() for i in selected):
            if 0 <= idx < len(self.groups):
                remove_paths.extend(self.groups[idx]["remove"])

        # deduplicate preserve order
        remove_paths = list(dict.fromkeys(remove_paths))

        msg = "Die folgenden Dateien werden in den Papierkorb verschoben:\n" + "\n".join(str(p) for p in remove_paths)
        reply = QMessageBox.question(self, "Bestätigung: Löschen", msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        cursor = self.conn.cursor()
        project_root = Path(__file__).resolve().parents[3]
        trash_dir = project_root / ".trash"
        trash_dir.mkdir(parents=True, exist_ok=True)

        for p in remove_paths:
            try:
                src = Path(p)
                if src.exists():
                    # move to trash with unique name
                    name = f"{int(time.time())}_{uuid.uuid4().hex}_{src.name}"
                    dst = trash_dir / name
                    shutil.move(str(src), str(dst))
                    # mark in DB as deleted and store trash path
                    cursor.execute(
                        "UPDATE files SET is_deleted = 1, trash_path = ?, deleted_at = ? WHERE path = ?",
                        (str(dst), time.time(), str(p)),
                    )
                else:
                    # still mark as deleted if DB entry exists
                    cursor.execute(
                        "UPDATE files SET is_deleted = 1, trash_path = NULL, deleted_at = ? WHERE path = ?",
                        (time.time(), str(p)),
                    )
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Fehler beim Verschieben von {p}: {e}")

        self.conn.commit()
        QMessageBox.information(self, "Fertig", "Ausgewählte Dateien wurden in den Papierkorb verschoben.")
        self.load_groups()

    def on_selection_changed(self, *_args) -> None:
        sel = self.list_widget.selectedIndexes()
        if not sel:
            self.preview.clear()
            self.meta_label.setText("Wähle eine Gruppe, um Details zu sehen.")
            self.delete_btn.setEnabled(False)
            self.keep_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            return

        # prefer first selected item
        idx = sel[0].row()
        if 0 <= idx < len(self.groups):
            group = self.groups[idx]
            keep = group["keep"]
            remove = group["remove"]
            meta = f"Keep: {Path(keep).name} ({len(remove)} to remove)\n"
            meta += "Remove list:\n" + "\n".join(str(p.name if isinstance(p, Path) else Path(p).name) for p in remove[:10])
            self.meta_label.setText(meta)
            try:
                if Path(keep).exists():
                    t = get_thumbnail(keep, (self.preview.width(), self.preview.height()))
                    pix = QPixmap(str(t))
                    self.preview.setPixmap(pix)
                else:
                    self.preview.setText("(file not found)")
            except (OSError, TypeError, RuntimeError):
                logger.debug(f"Failed to load preview", exc_info=True)
                self.preview.setText("(preview error)")

        self.delete_btn.setEnabled(True)
        self.keep_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)

    def _apply_filter(self, text: str) -> None:
        self._current_filter = text.lower().strip()
        self.list_widget.clear()
        for g in self.groups:
            if not self._current_filter or self._current_filter in g["title"].lower():
                item = QListWidgetItem(g["title"])
                try:
                    if g["keep"].exists():
                        pix = QPixmap(str(g["keep"])) .scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                       (OSError, TypeError, RuntimeError):
                    logger.debug(f"Failed to create filter thumbnail", exc_info=True)xception:
                    pass
                self.list_widget.addItem(item)

    def _mark_keep(self) -> None:
        # Mark first selected group's keep file (visual only placeholder)
        sel = self.list_widget.selectedIndexes()
        if not sel:
            return
        idx = sel[0].row()
        if 0 <= idx < len(self.groups):
            group = self.groups[idx]
            keep = group.get('keep')
            remove = group.get('remove', [])
            cursor = self.conn.cursor()
            try:
                # Clear any previous keeper flags for the files in this group
                paths = [str(keep)] + [str(p) for p in remove]
                cursor.execute(f"UPDATE files SET is_keeper = 0 WHERE path IN ({','.join('?' for _ in paths)})", paths)
                # Set keeper flag on chosen keep file
                cursor.execute("UPDATE files SET is_keeper = 1 WHERE path = ?", (str(keep),))
                self.conn.commit()
                QMessageBox.information(self, "Behalten", f"{keep} als Keeper markiert und gespeichert.")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Fehler beim Setzen des Keep-Flags: {e}")
            # Reload groups to reflect changes
            self.load_groups()

    def _undo_last_delete(self) -> None:
        """Restore the most recently deleted file from the project .trash and clear its deleted flag."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT file_id, path, trash_path FROM files WHERE is_deleted = 1 ORDER BY deleted_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            QMessageBox.information(self, "Papierkorb", "Keine gelöschten Dateien gefunden.")
            return

        file_id = row[0]
        orig_path = Path(row[1])
        trash_path = row[2]
        if not trash_path:
            QMessageBox.warning(self, "Papierkorb", "Gelöschte Datei konnte nicht gefunden werden (kein trash_path).")
            return

        trash_file = Path(trash_path)
        if not trash_file.exists():
            QMessageBox.warning(self, "Papierkorb", f"Datei im Papierkorb nicht gefunden: {trash_file}")
            return

        # restore
        try:
            orig_parent = orig_path.parent
            orig_parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(trash_file), str(orig_path))
            cursor.execute(
                "UPDATE files SET is_deleted = 0, trash_path = NULL, deleted_at = NULL WHERE file_id = ?",
                (file_id,),
            )
            self.conn.commit()
            QMessageBox.information(self, "Wiederhergestellt", f"{orig_path} wurde wiederhergestellt.")
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Wiederherstellung fehlgeschlagen: {e}")

        self.load_groups()

    def _on_trash_selection_changed(self) -> None:
        sel = self.trash_list.selectedIndexes()
        has = bool(sel)
        self.restore_selected_btn.setEnabled(has)
        self.perm_delete_btn.setEnabled(has)

    def _load_trash(self) -> None:
        """Load deleted files into the trash_list widget."""
        self.trash_list.clear()
        cursor = self.conn.cursor()
        cursor.execute("SELECT file_id, path, trash_path, deleted_at FROM files WHERE is_deleted = 1 ORDER BY deleted_at DESC")
        rows = cursor.fetchall()
        for r in rows:
            fid = r[0]
            path = r[1]
            trash_path = r[2] if len(r) > 2 else None
            deleted_at = r[3] if len(r) > 3 else None
            display = f"{Path(path).name} — {Path(path)}"
            if deleted_at:
                try:
                    dis(ValueError, TypeError):
                    logger.debug(f"Failed to format deleted_at timestamp", exc_info=True)xception:
                    pass
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, fid)
            # store trash_path for convenience
            item.setData(Qt.UserRole + 1, trash_path)
            self.trash_list.addItem(item)

    def _restore_selected(self) -> None:
        items = self.trash_list.selectedItems()
        if not items:
            return
        cursor = self.conn.cursor()
        project_root = Path(__file__).resolve().parents[3]
        for it in items:
            fid = it.data(Qt.UserRole)
            trash_path = it.data(Qt.UserRole + 1)
            cursor.execute("SELECT path FROM files WHERE file_id = ?", (fid,))
            row = cursor.fetchone()
            if not row:
                continue
            orig_path = Path(row[0])
            if trash_path and Path(trash_path).exists():
                try:
                    Path(orig_path).parent.mkdir(parents=True, exist_ok=True)
                    shu(OSError, PermissionError) as e:
                    logger.error(f"Restore failed: {e}", exc_info=True)path, orig_path)
                except Exception as e:
                    QMessageBox.warning(self, "Fehler", f"Wiederherstellung fehlgeschlagen: {e}")
                    continue
            # clear flags in DB
            cursor.execute("UPDATE files SET is_deleted = 0, trash_path = NULL, deleted_at = NULL WHERE file_id = ?", (fid,))
        self.conn.commit()
        QMessageBox.information(self, "Wiederhergestellt", "Ausgewählte Dateien wurden wiederhergestellt.")
        self.load_groups()

    def _perm_delete_selected(self) -> None:
        items = self.trash_list.selectedItems()
        if not items:
            return
        cursor = self.conn.cursor()
        # confirm
        msg = "Die ausgewählten Dateien dauerhaft löschen?"
        reply = QMessageBox.question(self, "Endgültig löschen", msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        for it in items:
            fid = it.data(Qt.UserRole)
            trash_path = it.data(Qt.UserRole + 1)
            # remove trash file
            try:
                if trash_path and Path(trash_path).exists():
                   OSError:
                logger.debug(f"Failed to delete trash file", exc_info=True)xception:
                pass
            # remove DB row
            try:
                cursqlite3.Error:
                logger.debug(f"Failed to delete from database", exc_info=True)xception:
                pass
        self.conn.commit()
        QMessageBox.information(self, "Gelöscht", "Ausgewählte Dateien wurden endgültig gelöscht.")
        self.load_groups()


class PlanDialog(QDialog):
    """Dialog that shows planned moves and asks for confirmation."""

    def __init__(self, parent, moves: list[tuple[str, str]]):
        super().__init__(parent)
        self.setWindowTitle("Vorschau: geplante Verschiebungen")
        self.resize(700, 400)
        layout = QVBoxLayout(self)
        info = QLabel(f"Geplante Verschiebungen: {len(moves)} Dateien")
        layout.addWidget(info)
        txt = QTextEdit()
        txt.setReadOnly(True)
        sb = [f"{src} -> {dst}" for src, dst in moves]
        txt.setPlainText("\n".join(sb))
        layout.addWidget(txt)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def run_ui(db_path: str | Path = "photo_cleaner.db") -> None:
    app = QApplication([])
    w = CleanupUI(db_path)
    w.show()
    app.exec()


if __name__ == "__main__":
    run_ui()
