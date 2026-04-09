"""
PhotoCleaner Main Window (ITIL UI)

** STATUS: DEPRECATED LEGACY UI **
Nur noch für Kompatibilität/Debugzwecke; nicht mehr primärer Einstieg.

Dieses ITIL-UI ist ein Legacy-Pfad:
- PySide6-basiert mit professionellem Design
- Umfassende Features: Status-Management, History-Tracking, Batch-Operations
- Integration mit allen Services und Repositories
- Themes, Hotkeys, Panels wie im Original-Design

Primäre UI ist `photo_cleaner.ui.modern_window.ModernMainWindow`.

Verwendung:
    python run_ui.py --db photo_cleaner.db
"""

from __future__ import annotations

import logging
import sqlite3
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QKeySequence, QPalette, QPixmap, QColor, QBrush, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from photo_cleaner.db.schema import Database
from photo_cleaner.config import AppConfig
from photo_cleaner.models.mode import AppMode
from photo_cleaner.models.status import FileStatus
from photo_cleaner.repositories.file_repository import FileRepository
from photo_cleaner.repositories.history_repository import HistoryRepository
from photo_cleaner.services.mode_service import ModeService
from photo_cleaner.services.progress_service import ProgressService
from photo_cleaner.services.rule_simulator import RuleSimulator
from photo_cleaner.services.status_service import StatusService
from photo_cleaner.ui.thumbnail_cache import get_thumbnail
from photo_cleaner.ui_actions import UIActions
from photo_cleaner.i18n import t

logger = logging.getLogger(__name__)


STATUS_COLORS = {
    FileStatus.KEEP.value: "#4CAF50",
    FileStatus.DELETE.value: "#F44336",
    FileStatus.UNSURE.value: "#FFEB3B",
    FileStatus.UNDECIDED.value: "#9E9E9E",
}


@dataclass
class GroupRow:
    group_id: str
    sample_path: Path
    total: int
    open_count: int
    decided_count: int
    delete_count: int
    similarity: float


@dataclass
class FileRow:
    path: Path
    status: FileStatus
    locked: bool
    is_recommended: bool = False


class HotkeyOverlay(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{t('hotkey_title')}")
        self.setModal(True)
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Navigation:</b>"))
        layout.addWidget(QLabel(t("hotkey_switch_group")))
        layout.addWidget(QLabel("  Links/Rechts - Bild navigieren"))
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("<b>Aktionen:</b>"))
        layout.addWidget(QLabel("  K - Keep (behalten)"))
        layout.addWidget(QLabel("  D - Delete (l\u00f6schen markieren)"))
        layout.addWidget(QLabel("  U - Unsure (unsicher)"))
        layout.addWidget(QLabel("  Space - Lock/Unlock"))
        layout.addWidget(QLabel("  Z - Undo letzte Aktion"))
        layout.addWidget(QLabel("  F - Fullscreen Vorschau"))
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("<b>UI-Steuerung (Dropdowns hinzugef\u00fcgt):</b>"))
        layout.addWidget(QLabel("  Mode-Dropdown - SAFE/REVIEW/CLEANUP w\u00e4hlen"))
        layout.addWidget(QLabel("  Theme-Dropdown - Dark/Light/System/High-Contrast"))
        layout.addWidget(QLabel("  ? - Dieses Overlay"))
        layout.addWidget(QLabel("  Strg+F - Suche"))
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)


class MainWindow(QMainWindow):
    def __init__(self, db_path: Path, output_path: Optional[Path] = None) -> None:
        super().__init__()
        warnings.warn(
            "MainWindow ist deprecated; bitte ModernMainWindow verwenden.",
            FutureWarning,
            stacklevel=2,
        )
        logger.warning("[DEPRECATED] MainWindow instantiated; use ModernMainWindow instead.")
        self.setWindowTitle("PhotoCleaner - Review")
        self.resize(1280, 800)

        self.db_path = Path(db_path)
        self.output_path = output_path  # Output-Ordner für Export
        self.db = Database(self.db_path)
        self.conn: sqlite3.Connection = self.db.connect()

        self.files = FileRepository(self.conn)
        self.history = HistoryRepository(self.conn)
        self.mode_svc = ModeService(self.conn)
        self.progress_svc = ProgressService(self.files)
        # Keep safe-mode lenient by default; UI still respects capabilities.
        self.mode_svc.set_mode(AppMode.CLEANUP_MODE)
        self.rule_sim = RuleSimulator(
            self.files,
            image_meta_loader=lambda _p: {},
            mode_getter=self.mode_svc.get_mode,
            is_exact_duplicate=lambda _p: True,
        )
        self.status_svc = StatusService(
            self.files, self.history, self.mode_svc.get_mode, is_exact_duplicate=lambda _p: True
        )
        # PHASE 4 FIX 1: Initialize CameraCalibrator and cache for ML learning
        from photo_cleaner.pipeline.camera_calibrator import CameraCalibrator
        from photo_cleaner.cache.image_cache_manager import ImageCacheManager
        
        self.cache_manager = ImageCacheManager(self.conn)
        self.camera_calibrator = CameraCalibrator(self.conn)
        
        self.actions = UIActions(
            self.files,
            self.history,
            self.mode_svc,
            self.progress_svc,
            self.rule_sim,
            self.status_svc,
            camera_calibrator=self.camera_calibrator,
            cache_manager=self.cache_manager,
        )

        self.groups: List[GroupRow] = []
        self.group_lookup: dict[str, GroupRow] = {}
        self.files_in_group: List[FileRow] = []
        self.current_group: Optional[str] = None
        self.current_index: int = -1
        
        # Theme tracking (added for Theme Dropdown)
        self.current_theme = "Dark"  # Default theme

        self._build_ui()
        self._wire_shortcuts()
        self._sync_mode_display()
        self._update_button_states()  # Initialize button states based on mode
        self.refresh_groups()
        self._update_progress()
        self._apply_dark_palette()

    # ---------- UI construction ----------

    def _build_ui(self) -> None:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)

        layout.addLayout(self._build_top_bar())
        # Path-Bar entfernt - Pfade werden beim Start gewählt

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_group_panel())
        splitter.addWidget(self._build_view_panel())
        splitter.addWidget(self._build_info_panel())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 3)
        layout.addWidget(splitter)

        layout.addWidget(self._build_status_bar())
        self.setCentralWidget(wrapper)

    def _build_top_bar(self) -> QHBoxLayout:
        """Build top action bar with Mode and Theme dropdowns (added in UI enhancement)."""
        bar = QHBoxLayout()
        
        # Mode Dropdown (replaces cycle button)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["SAFE_MODE", "REVIEW_MODE", "CLEANUP_MODE"])
        self.mode_combo.setCurrentText(self.mode_svc.get_mode().name)
        self.mode_combo.setFixedWidth(150)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self.mode_combo.setToolTip(t("app_mode_tooltip"))

        # Theme Dropdown (replaces toggle button)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System", "High-Contrast"])
        self.theme_combo.setCurrentText(self.current_theme)
        self.theme_combo.setFixedWidth(140)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        self.theme_combo.setToolTip(t("ui_theme_tooltip"))

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Suchen (Datei, Gruppe)")
        self.search_box.textChanged.connect(self._apply_group_filter)

        self.refresh_btn = QPushButton("Aktualisieren")
        self.refresh_btn.clicked.connect(self.refresh_groups)

        self.hotkey_btn = QToolButton()
        self.hotkey_btn.setText("?")
        self.hotkey_btn.clicked.connect(self._show_hotkeys)

        bar.addWidget(QLabel("Modus"))
        bar.addWidget(self.mode_combo)
        bar.addWidget(QLabel("Theme"))
        bar.addWidget(self.theme_combo)
        bar.addWidget(self.search_box, stretch=2)
        bar.addWidget(self.refresh_btn)
        bar.addWidget(self.hotkey_btn)
        return bar

    # ENTFERNT: _build_path_bar - Pfade werden beim Start über StartDialog gewählt
    # Die alte Path-Bar wird im neuen Workflow nicht mehr benötigt

    def _build_group_panel(self) -> QWidget:
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.addWidget(QLabel(t("groups")))
        self.group_list = QListWidget()
        self.group_list.itemSelectionChanged.connect(self._on_group_selected)
        self.group_list.setAlternatingRowColors(True)
        v.addWidget(self.group_list)
        return panel

    def _build_view_panel(self) -> QWidget:
        panel = QWidget()
        v = QVBoxLayout(panel)

        self.hero = QLabel("Keine Auswahl")
        self.hero.setAlignment(Qt.AlignCenter)
        self.hero.setMinimumHeight(420)
        self.hero.setMaximumHeight(550)
        self.hero.setFrameShape(QFrame.StyledPanel)
        self.hero.setScaledContents(False)
        v.addWidget(self.hero)

        actions = QHBoxLayout()
        self.keep_btn = QPushButton("Keep (K)")
        self.del_btn = QPushButton("Delete (D)")
        self.unsure_btn = QPushButton("Unsure (U)")
        self.lock_btn = QPushButton("Lock (Space)")
        self.undo_btn = QPushButton("Undo (Z)")
        for b in (self.keep_btn, self.del_btn, self.unsure_btn, self.lock_btn, self.undo_btn):
            actions.addWidget(b)
        v.addLayout(actions)

        self.thumb_list = QListWidget()
        self.thumb_list.setViewMode(QListWidget.IconMode)
        self.thumb_list.setIconSize(QSize(128, 128))
        self.thumb_list.setResizeMode(QListWidget.Adjust)
        self.thumb_list.setMovement(QListWidget.Static)
        self.thumb_list.setSpacing(8)
        self.thumb_list.itemClicked.connect(self._on_thumb_clicked)
        v.addWidget(self.thumb_list)

        self.keep_btn.clicked.connect(lambda: self._apply_status(FileStatus.KEEP))
        self.del_btn.clicked.connect(lambda: self._apply_status(FileStatus.DELETE))
        self.unsure_btn.clicked.connect(lambda: self._apply_status(FileStatus.UNSURE))
        self.lock_btn.clicked.connect(self._toggle_lock)
        self.undo_btn.clicked.connect(self._undo)

        return panel

    def _build_info_panel(self) -> QWidget:
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.addWidget(QLabel("Details"))

        self.tabs = QTabWidget()
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.exif_text = QTextEdit()
        self.exif_text.setReadOnly(True)
        self.actions_text = QTextEdit()
        self.actions_text.setReadOnly(True)
        self.tabs.addTab(self.info_text, "Info")
        self.tabs.addTab(self.exif_text, "EXIF")
        self.tabs.addTab(self.actions_text, "Aktionen")
        v.addWidget(self.tabs)
        return panel

    def _build_status_bar(self) -> QWidget:
        panel = QWidget()
        h = QHBoxLayout(panel)
        self.progress = QProgressBar()
        self.progress.setFormat("%p% Dateien entschieden")
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.status_label = QLabel("")
        
        # Finalisierungs-Button
        self.finalize_btn = QPushButton("Fertigstellen & Exportieren")
        self.finalize_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }")
        self.finalize_btn.clicked.connect(self._finalize_and_export)
        self.finalize_btn.setToolTip(t("finalize_export_tooltip"))
        
        h.addWidget(self.progress, stretch=2)
        h.addWidget(self.status_label)
        h.addWidget(self.finalize_btn)
        return panel

    # ---------- Data loading ----------

    def refresh_groups(self) -> None:
        self.groups = self._query_groups()
        self._render_groups()
        self.current_group = None
        self.files_in_group = []
        self.thumb_list.clear()
        self.hero.setText("Keine Auswahl")

    def _query_groups(self) -> List[GroupRow]:
        self.group_lookup = {}
        cur = self.conn.execute(
            """
            SELECT d.group_id,
                   MIN(f.path) AS sample_path,
                   COUNT(*) AS total,
                   SUM(CASE WHEN f.file_status IN ('UNDECIDED','UNSURE') THEN 1 ELSE 0 END) AS open_cnt,
                   SUM(CASE WHEN f.file_status IN ('KEEP','DELETE') THEN 1 ELSE 0 END) AS decided_cnt,
                   SUM(CASE WHEN f.file_status = 'DELETE' THEN 1 ELSE 0 END) AS delete_cnt,
                   MAX(d.similarity_score) AS sim
            FROM duplicates d
            JOIN files f ON f.file_id = d.file_id
            WHERE f.is_deleted = 0
            GROUP BY d.group_id
            ORDER BY (open_cnt > 0) DESC, open_cnt DESC, d.group_id
            """
        )
        rows = cur.fetchall()
        result: List[GroupRow] = []
        for r in rows:
            result.append(
                GroupRow(
                    group_id=str(r[0]),
                    sample_path=Path(r[1]),
                    total=r[2] or 0,
                    open_count=r[3] or 0,
                    decided_count=r[4] or 0,
                    delete_count=r[5] or 0,
                    similarity=float(r[6] or 0.0),
                )
            )
            self.group_lookup[result[-1].group_id] = result[-1]
        if not result:
            cur = self.conn.execute(
                """SELECT path, file_status, is_locked FROM files WHERE is_deleted = 0 
                   ORDER BY (file_status IN ('UNDECIDED','UNSURE')) DESC, path"""
            )
            rows = cur.fetchall()
            for idx, r in enumerate(rows):
                result.append(
                    GroupRow(
                        group_id=f"single-{idx}",
                        sample_path=Path(r[0]),
                        total=1,
                        open_count=0 if r[1] in (FileStatus.KEEP.value, FileStatus.DELETE.value) else 1,
                        decided_count=1 if r[1] in (FileStatus.KEEP.value, FileStatus.DELETE.value) else 0,
                        delete_count=1 if r[1] == FileStatus.DELETE.value else 0,
                        similarity=0.0,
                    )
                )
                self.group_lookup[result[-1].group_id] = result[-1]
        return result

    def _render_groups(self) -> None:
        self.group_list.clear()
        term = self.search_box.text().lower().strip()
        for g in self.groups:
            label = f"Gruppe {g.group_id} ({g.total})"
            if term and term not in label.lower() and term not in str(g.sample_path).lower():
                continue
            item = QListWidgetItem(label)
            chip = "Erledigt" if g.open_count == 0 else "Offen"
            item.setData(Qt.UserRole, g.group_id)
            item.setToolTip(f"Open {g.open_count} / Decided {g.decided_count} / Del {g.delete_count}")
            color = "#4CAF50" if g.open_count == 0 else "#FFEB3B" if g.delete_count else "#9E9E9E"
            item.setBackground(self._color_brush(color, alpha=40))
            self.group_list.addItem(item)

    # ---------- Group selection ----------

    def _on_group_selected(self) -> None:
        items = self.group_list.selectedItems()
        if not items:
            return
        group_id = items[0].data(Qt.UserRole)
        self.current_group = group_id
        self._load_group_files(group_id)

    def _load_group_files(self, group_id: str) -> None:
        if group_id.startswith("single-"):
            grp = self.group_lookup.get(group_id)
            if not grp:
                return
            cur = self.conn.execute(
                "SELECT path, file_status, is_locked, COALESCE(is_recommended, 0) FROM files WHERE path = ? AND is_deleted = 0",
                (str(grp.sample_path),),
            )
            rows = cur.fetchall()
        else:
            cur = self.conn.execute(
                """
                SELECT f.path, f.file_status, f.is_locked, COALESCE(f.is_recommended, 0)
                FROM files f
                JOIN duplicates d ON f.file_id = d.file_id
                WHERE d.group_id = ? AND f.is_deleted = 0
                ORDER BY COALESCE(f.is_recommended, 0) DESC, f.file_status = 'KEEP' DESC, f.path
                """,
                (group_id,),
            )
            rows = cur.fetchall()
        self.files_in_group = [FileRow(Path(r[0]), FileStatus(r[1]), bool(r[2]), bool(r[3])) for r in rows]
        self.thumb_list.clear()
        for idx, fr in enumerate(self.files_in_group):
            icon = self._thumb_icon(fr.path)
            # Add star badge for recommended images
            display_name = fr.path.name
            if fr.is_recommended:
                display_name = f"RECOMMENDED {display_name}"
            item = QListWidgetItem(icon, display_name)
            badge = " (LOCK)" if fr.locked else ""
            if fr.is_recommended:
                badge += " (EMPFOHLEN)"
            item.setToolTip(f"{fr.path}{badge}\nStatus: {fr.status.value}")
            item.setData(Qt.UserRole, idx)
            # Use green background for recommended images
            if fr.is_recommended:
                color = "#4CAF50"  # Green for recommended
                item.setBackground(self._color_brush(color, alpha=80))
            else:
                color = STATUS_COLORS.get(fr.status.value, "#9E9E9E")
                item.setBackground(self._color_brush(color, alpha=40))
            self.thumb_list.addItem(item)
        if self.files_in_group:
            self.thumb_list.setCurrentRow(0)
            self._set_current_index(0)

    # ---------- Actions ----------

    def _on_thumb_clicked(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.UserRole)
        if idx is not None:
            self._set_current_index(int(idx))

    def _set_current_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.files_in_group):
            return
        self.current_index = idx
        fr = self.files_in_group[idx]
        self._update_preview(fr)
        self._update_details(fr)

    def _apply_status(self, status: FileStatus) -> None:
        fr = self._current_file()
        if not fr:
            return
        if status == FileStatus.DELETE:
            res = self.actions.ui_set_delete(fr.path)
        elif status == FileStatus.KEEP:
            res = self.actions.ui_set_keep(fr.path)
            # When user manually sets KEEP, make this the new recommendation
            self._set_recommended(fr.path)
        elif status == FileStatus.UNSURE:
            res = self.actions.ui_set_unsure(fr.path)
        else:
            res = self.actions.ui_set_undecided(fr.path)
        self._show_status(res)
        self._reload_after_action()

    def _toggle_lock(self) -> None:
        fr = self._current_file()
        if not fr:
            return
        res = self.actions.ui_toggle_lock(fr.path)
        self._show_status(res)
        self._reload_after_action()

    def _undo(self) -> None:
        res = self.actions.ui_undo()
        self._show_status(res)
        self._reload_after_action()

    def _reload_after_action(self) -> None:
        if self.current_group:
            saved_idx = self.current_index
            self._load_group_files(self.current_group)
            # Restore selection after reload and update thumbnail color
            if 0 <= saved_idx < len(self.files_in_group):
                self.thumb_list.setCurrentRow(saved_idx)
                self._set_current_index(saved_idx)
                # Update thumbnail background to reflect new status
                fr = self.files_in_group[saved_idx]
                item = self.thumb_list.item(saved_idx)
                if item:
                    color = STATUS_COLORS.get(fr.status.value, "#9E9E9E")
                    item.setBackground(self._color_brush(color, alpha=40))
        self._update_progress()

    def _set_recommended(self, path: Path) -> None:
        """Set the given image as recommended and clear all other recommendations in the group."""
        if not self.current_group:
            return
        try:
            # Clear all recommendations in the current group
            self.conn.execute(
                """
                UPDATE files
                SET is_recommended = 0, keeper_source = 'undecided'
                WHERE file_id IN (
                    SELECT f.file_id
                    FROM files f
                    JOIN duplicates d ON f.file_id = d.file_id
                    WHERE d.group_id = ?
                )
                """,
                (self.current_group,),
            )
            # Set the new recommendation
            self.conn.execute(
                "UPDATE files SET is_recommended = 1, keeper_source = 'manual' WHERE path = ?",
                (str(path),),
            )
            self.conn.commit()
        except Exception as e:
            print(f"Error setting recommendation: {e}")

    # ---------- Rendering helpers ----------

    def _update_preview(self, fr: FileRow) -> None:
        try:
            thumb_path = get_thumbnail(fr.path, (900, 600))
            pix = QPixmap(str(thumb_path))
            # Scale to fixed max size to prevent layout shifts
            scaled = pix.scaled(800, 550, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.hero.setPixmap(scaled)
        except (OSError, TypeError, RuntimeError):
            logger.debug(f"Failed to load preview for {fr.path.name}", exc_info=True)
            self.hero.setText(f"{fr.path.name}\n(Vorschau nicht verfuegbar)")

    def _update_details(self, fr: FileRow) -> None:
        status_icons = {
            FileStatus.KEEP.value: "KEEP",
            FileStatus.DELETE.value: "DELETE",
            FileStatus.UNSURE.value: "? UNSURE",
            FileStatus.UNDECIDED.value: "○ UNDECIDED",
        }
        status_display = status_icons.get(fr.status.value, fr.status.value)
        info = [
            f"Status: {status_display}",
            f"Locked: {'JA' if fr.locked else 'NEIN'}",
        ]
        if fr.is_recommended:
            info.append("EMPFOHLEN (Auto-Auswahl)")
        info.append("")
        info.append(f"Pfad: {fr.path}")
        try:
            st = fr.path.stat()
            info.append(f"Groesse: {st.st_size:,} bytes")
            from datetime import datetime
            dt = datetime.fromtimestamp(st.st_mtime)
            info.append(f"Geaendert: {dt.strftime('%Y-%m-%d %H:%M')}")
        except OSError:
            logger.debug(f"Failed to stat {fr.path.name}", exc_info=True)
        self.info_text.setPlainText("\n".join(info))
        self.exif_text.setPlainText("EXIF / Metadaten hier anzeigen")
        self.actions_text.setPlainText("Hotkeys: K/D/U/Space, Undo: Z, Gruppen: Ctrl+J / Ctrl+K")

    def _thumb_icon(self, path: Path) -> QIcon:
        try:
            thumb_path = get_thumbnail(path, (196, 196))
            return QIcon(str(thumb_path))
        except (OSError, TypeError, RuntimeError):
            logger.debug(f"Failed to create icon for {path.name}", exc_info=True)
            return QIcon()

    def _show_status(self, res: dict) -> None:
        if res.get("ok"):
            self.status_label.setText("Aktion erfolgreich")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            return
        msg = res.get("message") or res.get("error") or "Fehler"
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("color: #F44336; font-weight: bold;")

    def _update_progress(self) -> None:
        res = self.actions.ui_get_progress()
        if not res.get("ok"):
            return
        total = res.get("files_total", 0)
        decided = res.get("files_decided", 0)
        pct = int((decided / total) * 100) if total else 0
        self.progress.setMaximum(100)
        self.progress.setValue(pct)
        self.status_label.setText(
            f"Total {total} | Decided {decided} | Open {res.get('files_open', 0)} | Groups done {res.get('groups_done', 0)}/{res.get('groups_total', 0)}"
        )

    def _apply_group_filter(self) -> None:
        self._render_groups()

    # ---------- Utilities ----------

    def _color_brush(self, color: str, alpha: int = 30) -> QBrush:
        qcolor = QColor(color)
        qcolor.setAlpha(alpha)
        return QBrush(qcolor)

    def _apply_dark_palette(self) -> None:
        pal = QPalette()
        pal.setColor(QPalette.Window, Qt.black)
        pal.setColor(QPalette.WindowText, Qt.white)
        pal.setColor(QPalette.Base, Qt.black)
        pal.setColor(QPalette.AlternateBase, Qt.darkGray)
        pal.setColor(QPalette.Text, Qt.white)
        pal.setColor(QPalette.Button, Qt.darkGray)
        pal.setColor(QPalette.ButtonText, Qt.white)
        pal.setColor(QPalette.Highlight, Qt.gray)
        pal.setColor(QPalette.HighlightedText, Qt.white)
        self.setPalette(pal)
    
    def _apply_light_palette(self) -> None:
        """Apply light theme palette."""
        pal = QPalette()
        pal.setColor(QPalette.Window, Qt.white)
        pal.setColor(QPalette.WindowText, Qt.black)
        pal.setColor(QPalette.Base, Qt.white)
        pal.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
        pal.setColor(QPalette.Text, Qt.black)
        pal.setColor(QPalette.Button, QColor(240, 240, 240))
        pal.setColor(QPalette.ButtonText, Qt.black)
        pal.setColor(QPalette.Highlight, QColor(0, 120, 215))
        pal.setColor(QPalette.HighlightedText, Qt.white)
        self.setPalette(pal)
    
    def _apply_high_contrast_palette(self) -> None:
        """Apply high-contrast theme for accessibility."""
        pal = QPalette()
        pal.setColor(QPalette.Window, Qt.black)
        pal.setColor(QPalette.WindowText, Qt.yellow)
        pal.setColor(QPalette.Base, Qt.black)
        pal.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
        pal.setColor(QPalette.Text, Qt.yellow)
        pal.setColor(QPalette.Button, Qt.black)
        pal.setColor(QPalette.ButtonText, Qt.yellow)
        pal.setColor(QPalette.Highlight, Qt.cyan)
        pal.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(pal)

    def _on_theme_changed(self, theme_name: str) -> None:
        """Handle theme dropdown selection (added for Theme Dropdown feature).
        
        Live-switches between themes without data loss.
        Respects ITIL-UI design and keeps Action-Bar consistent.
        """
        self.current_theme = theme_name
        
        if theme_name == "Dark":
            self._apply_dark_palette()
        elif theme_name == "Light":
            self._apply_light_palette()
        elif theme_name == "System":
            # Use system default palette
            self.setPalette(QApplication.palette())
        elif theme_name == "High-Contrast":
            self._apply_high_contrast_palette()
        
        # Force refresh to apply theme to all widgets
        self.update()

    # ENTFERNT: _choose_input_path und _choose_output_path
    # Im neuen Workflow werden Pfade beim Start über StartDialog gewählt
    # Diese Methoden werden nicht mehr aufgerufen

    def _on_mode_changed(self, mode_name: str) -> None:
        """Handle mode dropdown selection (added for Mode Dropdown feature).
        
        Changes app mode instantly while respecting all backend guards:
        - SAFE_MODE: Read-only, no modifications
        - REVIEW_MODE: Can mark files, no deletion
        - CLEANUP_MODE: Full access including deletion
        
        Forwarded to ModeService via ui_actions.py facade.
        """
        mode_map = {
            "SAFE_MODE": AppMode.SAFE_MODE,
            "REVIEW_MODE": AppMode.REVIEW_MODE,
            "CLEANUP_MODE": AppMode.CLEANUP_MODE,
        }
        
        if mode_name in mode_map:
            new_mode = mode_map[mode_name]
            # Set mode through service (respects all guards)
            self.mode_svc.set_mode(new_mode)
            
            # Update UI to reflect mode capabilities
            self._update_button_states()
            
            # Log mode change
            print(f"Mode changed to: {mode_name}")

    def _sync_mode_display(self) -> None:
        """Sync mode dropdown with current mode (deprecated display field removed)."""
        current_mode = self.mode_svc.get_mode()
        self.mode_combo.setCurrentText(current_mode.name)
    
    def _update_button_states(self) -> None:
        """Update button enabled states based on current mode."""
        current_mode = self.mode_svc.get_mode()
        
        # SAFE_MODE: All modification buttons disabled
        if current_mode == AppMode.SAFE_MODE:
            self.keep_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
            self.unsure_btn.setEnabled(False)
            self.lock_btn.setEnabled(False)
            self.undo_btn.setEnabled(False)
        # REVIEW_MODE: Can mark, but cannot delete through UI
        elif current_mode == AppMode.REVIEW_MODE:
            self.keep_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
            self.unsure_btn.setEnabled(True)
            self.lock_btn.setEnabled(True)
            self.undo_btn.setEnabled(True)
        # CLEANUP_MODE: Full access
        else:
            self.keep_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
            self.unsure_btn.setEnabled(True)
            self.lock_btn.setEnabled(True)
            self.undo_btn.setEnabled(True)

    # ENTFERNT: _load_paths_from_meta und _save_paths_to_meta
    # Im neuen Workflow werden Pfade beim Start über StartDialog gewählt
    # und als Parameter übergeben (self.output_path)
    # Die metadata-Tabelle wird nicht mehr für Pfade verwendet

    def _show_hotkeys(self) -> None:
        HotkeyOverlay(self).exec()

    def _wire_shortcuts(self) -> None:
        QShortcut(QKeySequence("K"), self, activated=lambda: self._apply_status(FileStatus.KEEP))
        QShortcut(QKeySequence("D"), self, activated=lambda: self._apply_status(FileStatus.DELETE))
        QShortcut(QKeySequence("U"), self, activated=lambda: self._apply_status(FileStatus.UNSURE))
        QShortcut(QKeySequence("Space"), self, activated=self._toggle_lock)
        QShortcut(QKeySequence("Z"), self, activated=self._undo)
        QShortcut(QKeySequence("Ctrl+J"), self, activated=self._group_next)
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._group_prev)
        QShortcut(QKeySequence("Right"), self, activated=self._file_next)
        QShortcut(QKeySequence("Left"), self, activated=self._file_prev)
        QShortcut(QKeySequence("?"), self, activated=self._show_hotkeys)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.search_box.setFocus())

    def _group_next(self) -> None:
        row = self.group_list.currentRow()
        if row < self.group_list.count() - 1:
            self.group_list.setCurrentRow(row + 1)

    def _group_prev(self) -> None:
        row = self.group_list.currentRow()
        if row > 0:
            self.group_list.setCurrentRow(row - 1)

    def _file_next(self) -> None:
        if self.current_index + 1 < len(self.files_in_group):
            self._set_current_index(self.current_index + 1)
            self.thumb_list.setCurrentRow(self.current_index)

    def _file_prev(self) -> None:
        if self.current_index - 1 >= 0:
            self._set_current_index(self.current_index - 1)
            self.thumb_list.setCurrentRow(self.current_index)

    def _current_file(self) -> Optional[FileRow]:
        if 0 <= self.current_index < len(self.files_in_group):
            return self.files_in_group[self.current_index]
        return None

    def _finalize_and_export(self) -> None:
        """Finalisiert Review und exportiert KEEP-Bilder."""
        from PySide6.QtWidgets import QMessageBox
        from photo_cleaner.exporter import Exporter
        
        # Prüfe ob Output-Pfad gesetzt ist
        if not self.output_path:
            QMessageBox.warning(
                self,
                "Kein Output-Ordner",
                t("no_output_folder_msg")
            )
            return
        
        # Bestätigungsdialog
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM files WHERE file_status = 'KEEP' AND is_deleted = 0"
        )
        keep_count = cur.fetchone()[0]
        
        if keep_count == 0:
            QMessageBox.information(
                self,
                "Keine Auswahl",
                "Es wurden keine Bilder zum Behalten markiert."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Fertigstellen?",
            f"{keep_count} Bild(er) wurden als KEEP markiert.\n\n"
            f"Diese werden in folgende Struktur exportiert:\n{self.output_path}/YYYY/MM/DD/\n\n"
            f"Möchten Sie fortfahren?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Export starten
        try:
            # Hole alle KEEP-Dateien
            cur = self.conn.execute(
                "SELECT path FROM files WHERE file_status = 'KEEP' AND is_deleted = 0"
            )
            keep_paths = [Path(row[0]) for row in cur.fetchall()]
            
            # Exportiere
            exporter = Exporter(self.output_path)
            success_count, failure_count, errors = exporter.export_files(keep_paths)
            
            # Zeige Ergebnis
            if failure_count == 0:
                QMessageBox.information(
                    self,
                    "Export erfolgreich",
                    f"{success_count} Bild(er) wurden erfolgreich exportiert nach:\n{self.output_path}"
                )
            else:
                error_text = "\n".join(errors[:5])  # Erste 5 Fehler
                if len(errors) > 5:
                    error_text += f"\n... und {len(errors) - 5} weitere"
                QMessageBox.warning(
                    self,
                    "Export teilweise fehlgeschlagen",
                    f"{success_count} Bild(er) erfolgreich exportiert\n{failure_count} Fehler\n\n{error_text}"
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export fehlgeschlagen",
                f"Fehler beim Export: {e}"
            )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            self.db.close()
        except sqlite3.Error:
            logger.debug("Failed to close database connection", exc_info=True)
        super().closeEvent(event)


def run_ui(db_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    win = MainWindow(Path(db_path))
    win.show()
    app.exec()


if __name__ == "__main__":
    run_ui(AppConfig.get_db_dir() / "photo_cleaner.db")
