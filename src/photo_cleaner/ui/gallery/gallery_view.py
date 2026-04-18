"""GalleryView — Haupt-Widget der Galerie.

Zeigt alle Bilder mit status=KEEP in einem paginierten Grid.
Unterstützt Filterung (Zeitraum, Score, Suche), Lazy-Thumbnail-Loading
und einen Slideshow-Modus.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QImage, QKeySequence, QShortcut, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from photo_cleaner.models.status import FileStatus
from photo_cleaner.ui.color_constants import (
    get_semantic_colors,
    get_text_hint_color,
    to_rgba,
)
from photo_cleaner.theme import get_theme_colors
from photo_cleaner.ui.gallery.gallery_card import GalleryCard
from photo_cleaner.ui.gallery.gallery_filter_bar import GalleryFilterBar, GalleryFilterOptions
from photo_cleaner.ui.thumbnail_lazy import SmartThumbnailCache, ThumbnailLoader
from photo_cleaner.i18n import t

logger = logging.getLogger(__name__)

PAGE_SIZE = 100   # Bilder pro Seite
COLS = 5          # Spalten im Grid


@dataclass
class GalleryEntry:
    path: Path
    quality_score: Optional[float]
    sharpness_component: Optional[float]
    lighting_component: Optional[float]
    resolution_component: Optional[float]
    face_quality_component: Optional[float]
    capture_time: Optional[float]   # unix timestamp
    exif_json: Optional[str]        # raw JSON, für Snippet-Auflösung


class GalleryView(QWidget):
    """Galerie-Widget: zeigt alle KEEP-Bilder, gefiltert und paginiert."""

    # Rückkanal an ModernMainWindow
    image_status_changed = Signal(object, object)  # (Path, FileStatus)
    gallery_closed = Signal()
    scan_requested = Signal()      # → ImportDialog öffnen
    review_requested = Signal()   # → Review-Workflow öffnen

    def __init__(self, db_path: Path, parent=None):
        super().__init__(parent)
        self._db_path = db_path

        # Alle Einträge (ungefiltert) und die aktuelle gefilterte+sortierte Ansicht
        self._all_entries: list[GalleryEntry] = []
        self._filtered_entries: list[GalleryEntry] = []

        # Aktuelle Seite
        self._current_page = 0

        # Aktive Karten (referenziert für Thumbnail-Callbacks)
        self._cards: list[GalleryCard] = []

        # Thumbnail-Loader (eigener, unabhängig vom MainWindow-Loader)
        self._thumb_cache = SmartThumbnailCache(max_size_mb=150)
        self._thumb_loader = ThumbnailLoader(self._thumb_cache, thumb_size=(200, 200))
        self._thumb_loader.thumbnail_loaded.connect(self._on_thumb_loaded)
        self._thumb_loader.start()
        self._thumb_loader.resume()

        # Slideshow
        self._slideshow_timer = QTimer(self)
        self._slideshow_timer.timeout.connect(self._slideshow_next)
        self._slideshow_index = 0
        self._slideshow_running = False
        self._slideshow_dialog: Optional[QDialog] = None
        self._slideshow_image_label: Optional[QLabel] = None
        self._slideshow_title_label: Optional[QLabel] = None

        self._build_ui()

    # ──────────────────────────────────────────────────────────────────────────
    # UI-Aufbau
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        colors = get_theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header-Leiste
        header = self._build_header()
        layout.addWidget(header)

        # Filter-Leiste
        self._filter_bar = GalleryFilterBar(self)
        self._filter_bar.filter_changed.connect(self._on_filter_changed)
        layout.addWidget(self._filter_bar)

        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Scroll-Bereich mit Grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {colors['window']}; }}"
        )

        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(12)
        self._grid_layout.setContentsMargins(16, 16, 16, 16)
        self._scroll.setWidget(self._grid_container)
        layout.addWidget(self._scroll, stretch=1)

        # Paginierung + Status
        layout.addWidget(self._build_footer())

        # Keyboard: Pfeiltasten für Slideshow / Navigation
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self._close_gallery)

    def _build_header(self) -> QWidget:
        colors = get_theme_colors()
        semantic = get_semantic_colors()

        header = QWidget()
        header.setStyleSheet(
            f"background-color: {colors['window']}; border-bottom: 1px solid {colors['border']};"
        )
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)

        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(self._title_label)

        layout.addStretch()

        # Review-Badge (anfangs versteckt, via show_review_badge() sichtbar)
        self._review_banner = QWidget()
        self._review_banner.setVisible(False)
        review_layout = QHBoxLayout(self._review_banner)
        review_layout.setContentsMargins(0, 0, 0, 0)
        review_layout.setSpacing(8)
        self._review_badge_label = QLabel()
        self._review_badge_label.setStyleSheet(
            f"font-size: 12px; color: {semantic['warning']}; font-weight: 600;"
        )
        review_layout.addWidget(self._review_badge_label)
        review_btn = QPushButton(t("review_open"))
        review_btn.setMinimumHeight(32)
        review_btn.clicked.connect(self.review_requested.emit)
        review_btn.setStyleSheet(
            f"QPushButton {{ padding: 6px 14px; border-radius: 8px; border: none; "
            f"background-color: {semantic['warning']}; color: white; font-size: 12px; font-weight: 600; }}"
        )
        review_layout.addWidget(review_btn)
        layout.addWidget(self._review_banner)

        return header

    def _build_footer(self) -> QWidget:
        colors = get_theme_colors()
        footer = QWidget()
        footer.setStyleSheet(
            f"background-color: {colors['window']}; border-top: 1px solid {colors['border']};"
        )
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(12, 6, 12, 6)

        self._prev_btn = QPushButton("←")
        self._prev_btn.setEnabled(False)
        self._prev_btn.clicked.connect(self._prev_page)
        self._prev_btn.setFixedSize(36, 28)
        layout.addWidget(self._prev_btn)

        self._page_label = QLabel("1/1")
        self._page_label.setStyleSheet(f"font-size: 12px; color: {colors['text']};")
        layout.addWidget(self._page_label)

        self._next_btn = QPushButton("→")
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._next_page)
        self._next_btn.setFixedSize(36, 28)
        layout.addWidget(self._next_btn)

        layout.addStretch()

        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"font-size: 12px; color: {get_text_hint_color()};")
        layout.addWidget(self._count_label)

        return footer

    # ──────────────────────────────────────────────────────────────────────────
    # Daten laden
    # ──────────────────────────────────────────────────────────────────────────

    def load_keep_images(self) -> None:
        """Lädt alle KEEP-Bilder aus der DB. Aufruf aus MainWindow."""
        self._all_entries = self._query_keep_images()
        self._apply_filter(GalleryFilterOptions())

    def refresh(self) -> None:
        """Neu laden nach externem Status-Change (z.B. Watch Folder Import)."""
        active_filter = self._filter_bar._build_filter() if hasattr(self, "_filter_bar") else GalleryFilterOptions()
        self._all_entries = self._query_keep_images()
        self._apply_filter(active_filter)

    def show_review_badge(self, group_count: int) -> None:
        """Zeigt den Review-Banner im Header (nach Analyse-Abschluss)."""
        if group_count > 0:
            label_text = t("gallery_review_badge").format(count=group_count)
            self._review_badge_label.setText(label_text)
            self._review_banner.setVisible(True)
        else:
            self._review_banner.setVisible(False)

    def start_slideshow(self) -> None:
        """Öffentlicher Einstiegspunkt für Menüs/Buttons."""
        if self._slideshow_running:
            return
        self._start_slideshow()

    def _query_keep_images(self) -> list[GalleryEntry]:
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT
                    f.path,
                    f.quality_score,
                    f.sharpness_component,
                    f.lighting_component,
                    f.resolution_component,
                    f.face_quality_component,
                    f.capture_time,
                    f.exif_json
                FROM files f
                WHERE f.file_status = 'KEEP'
                  AND f.is_deleted = 0
                ORDER BY f.quality_score DESC NULLS LAST, f.path ASC
                """
            )
            rows = cur.fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.error("GalleryView: DB-Fehler beim Laden: %s", e, exc_info=True)
            return []

        entries = []
        for row in rows:
            entries.append(
                GalleryEntry(
                    path=Path(row["path"]),
                    quality_score=row["quality_score"],
                    sharpness_component=row["sharpness_component"],
                    lighting_component=row["lighting_component"],
                    resolution_component=row["resolution_component"],
                    face_quality_component=row["face_quality_component"],
                    capture_time=row["capture_time"],
                    exif_json=row["exif_json"],
                )
            )
        return entries

    # ──────────────────────────────────────────────────────────────────────────
    # Filtern
    # ──────────────────────────────────────────────────────────────────────────

    def _on_filter_changed(self, opts: GalleryFilterOptions) -> None:
        self._current_page = 0
        self._apply_filter(opts)

    def set_filter(self, opts: GalleryFilterOptions) -> None:
        self._current_page = 0
        self._apply_filter(opts)

    def _apply_filter(self, opts: GalleryFilterOptions) -> None:
        results = []
        for entry in self._all_entries:
            # Score-Filter
            if opts.min_score > 0:
                score = entry.quality_score
                if score is None or score < opts.min_score:
                    continue

            # Datums-Filter
            if opts.date_from or opts.date_to:
                entry_date = self._entry_date(entry)
                if opts.date_from and (entry_date is None or entry_date < opts.date_from):
                    continue
                if opts.date_to and (entry_date is None or entry_date > opts.date_to):
                    continue

            # Suche
            if opts.search_text:
                needle = opts.search_text.lower()
                if needle not in entry.path.name.lower() and needle not in str(entry.path).lower():
                    continue

            results.append(entry)

        self._filtered_entries = results
        self._render_current_page()

    def _entry_date(self, entry: GalleryEntry) -> Optional[date]:
        if entry.capture_time:
            try:
                return datetime.fromtimestamp(entry.capture_time).date()
            except (OSError, ValueError):
                pass
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Rendering
    # ──────────────────────────────────────────────────────────────────────────

    def _render_current_page(self) -> None:
        self._clear_grid()
        self._thumb_loader.clear_queue()

        total = len(self._filtered_entries)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        self._current_page = min(self._current_page, total_pages - 1)

        start = self._current_page * PAGE_SIZE
        end = min(total, start + PAGE_SIZE)

        page_entries = self._filtered_entries[start:end]
        self._cards = []

        for local_idx, entry in enumerate(page_entries):
            global_idx = start + local_idx
            snippet = self._build_exif_snippet(entry)
            card = GalleryCard(
                path=entry.path,
                index=global_idx,
                quality_score=entry.quality_score,
                exif_snippet=snippet,
            )
            card.clicked.connect(self._on_card_clicked)
            card.status_change_requested.connect(self._on_status_change_requested)
            card.open_folder_requested.connect(self._on_open_folder_requested)

            row = local_idx // COLS
            col = local_idx % COLS
            self._grid_layout.addWidget(card, row, col)
            self._cards.append(card)

            # Thumbnail in Queue einstellen
            if entry.path.exists():
                self._thumb_loader.enqueue(global_idx, entry.path)

        # Leer-Zustand
        if not self._cards:
            self._show_empty_state()

        # Titelanzeige
        keep_count = len(self._all_entries)
        filtered_count = total
        if keep_count == filtered_count:
            self._title_label.setText(f"{t('gallery_title')} ({keep_count})")
        else:
            self._title_label.setText(f"{t('gallery_title')} ({filtered_count} / {keep_count})")

        # Paginierungs-Controls
        self._page_label.setText(f"{self._current_page + 1}/{total_pages}")
        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled(self._current_page < total_pages - 1)
        self._count_label.setText(
            f"{start + 1}–{end} {t('gallery_of')} {total}" if total > 0 else ""
        )

        self._scroll.verticalScrollBar().setValue(0)

    def _show_empty_state(self):
        hint_color = get_text_hint_color()
        semantic = get_semantic_colors()
        empty_label = QLabel(t("gallery_keep_empty"))
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet(
            f"font-size: 14px; color: {hint_color}; padding: 20px 40px 8px;"
        )
        self._grid_layout.addWidget(empty_label, 0, 0, 1, COLS)
        cta_btn = QPushButton(t("gallery_scan_cta"))
        cta_btn.setMinimumHeight(44)
        cta_btn.setMinimumWidth(200)
        cta_btn.clicked.connect(self.scan_requested.emit)
        cta_btn.setStyleSheet(
            f"QPushButton {{ padding: 10px 28px; border-radius: 10px; border: none; "
            f"background-color: {semantic['success']}; color: white; font-size: 14px; font-weight: 700; }}"
        )
        cta_container = QWidget()
        cta_layout = QHBoxLayout(cta_container)
        cta_layout.setAlignment(Qt.AlignCenter)
        cta_layout.addWidget(cta_btn)
        self._grid_layout.addWidget(cta_container, 1, 0, 1, COLS)

    def _clear_grid(self):
        for card in self._cards:
            card.cleanup()
            self._grid_layout.removeWidget(card)
            card.deleteLater()
        self._cards = []

        # Entferne sonstige Widgets (z.B. Empty-State-Labels)
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    # ──────────────────────────────────────────────────────────────────────────
    # Thumbnail-Callback
    # ──────────────────────────────────────────────────────────────────────────

    def _on_thumb_loaded(self, global_idx: int, qimg: QImage) -> None:
        """Callback vom ThumbnailLoader — läuft im UI-Thread (via Signal)."""
        page_start = self._current_page * PAGE_SIZE
        local_idx = global_idx - page_start
        if 0 <= local_idx < len(self._cards):
            self._cards[local_idx].set_thumbnail_image(qimg)

    # ──────────────────────────────────────────────────────────────────────────
    # Interaktion
    # ──────────────────────────────────────────────────────────────────────────

    def _on_card_clicked(self, global_idx: int) -> None:
        if 0 <= global_idx < len(self._filtered_entries):
            entry = self._filtered_entries[global_idx]
            self._open_detail(entry)

    def _open_detail(self, entry: GalleryEntry) -> None:
        """Öffnet das vorhandene ImageDetailWindow aus modern_window."""
        try:
            from photo_cleaner.ui.modern_window import FileRow, ImageDetailWindow
            from photo_cleaner.models.status import FileStatus

            file_row = FileRow(
                path=entry.path,
                status=FileStatus.KEEP,
                locked=False,
                is_recommended=False,
                quality_score=entry.quality_score,
                sharpness_score=entry.sharpness_component,
                lighting_score=entry.lighting_component,
                resolution_score=entry.resolution_component,
                face_quality_score=entry.face_quality_component,
            )
            # Kein parent_window-Rückkanal — Gallery ist read-mostly
            win = ImageDetailWindow(file_row, parent=None)
            win.show()
        except Exception as e:
            logger.error("GalleryView: Konnte Detail-Fenster nicht öffnen: %s", e, exc_info=True)

    def _on_status_change_requested(self, global_idx: int, new_status: FileStatus) -> None:
        if 0 <= global_idx < len(self._filtered_entries):
            path = self._filtered_entries[global_idx].path
            self._apply_status_to_db(path, new_status)
            self.image_status_changed.emit(path, new_status)
            # Nach Status-Änderung: Entry aus _all_entries entfernen wenn nicht mehr KEEP
            if new_status != FileStatus.KEEP:
                self._all_entries = [e for e in self._all_entries if e.path != path]
                self.refresh()

    def _apply_status_to_db(self, path: Path, new_status: FileStatus) -> None:
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                "UPDATE files SET file_status = ? WHERE path = ?",
                (new_status.value, str(path)),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error("GalleryView: Status-Update fehlgeschlagen: %s", e, exc_info=True)

    def _on_open_folder_requested(self, global_idx: int) -> None:
        if 0 <= global_idx < len(self._filtered_entries):
            path = self._filtered_entries[global_idx].path
            folder = path.parent
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    # ──────────────────────────────────────────────────────────────────────────
    # Paginierung
    # ──────────────────────────────────────────────────────────────────────────

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._render_current_page()

    def _next_page(self):
        total_pages = max(1, (len(self._filtered_entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        if self._current_page < total_pages - 1:
            self._current_page += 1
            self._render_current_page()

    # ──────────────────────────────────────────────────────────────────────────
    # Slideshow
    # ──────────────────────────────────────────────────────────────────────────

    def _toggle_slideshow(self):
        if self._slideshow_running:
            self._stop_slideshow()
        else:
            self._start_slideshow()

    def _start_slideshow(self):
        if not self._filtered_entries:
            return
        self._slideshow_running = True
        self._slideshow_index = self._current_page * PAGE_SIZE  # starte bei aktueller Seite
        self._ensure_slideshow_dialog()
        self._show_slideshow_entry(self._filtered_entries[self._slideshow_index])
        self._slideshow_index = (self._slideshow_index + 1) % len(self._filtered_entries)
        self._slideshow_timer.start(3000)  # 3 Sekunden pro Bild

    def _stop_slideshow(self, close_dialog: bool = True):
        self._slideshow_running = False
        self._slideshow_timer.stop()
        if close_dialog and self._slideshow_dialog is not None:
            self._slideshow_dialog.close()

    def _slideshow_next(self):
        if not self._filtered_entries:
            self._stop_slideshow()
            return
        entry = self._filtered_entries[self._slideshow_index]
        self._show_slideshow_entry(entry)
        self._slideshow_index = (self._slideshow_index + 1) % len(self._filtered_entries)

    def _ensure_slideshow_dialog(self) -> None:
        if self._slideshow_dialog is not None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(t("gallery_slideshow_start"))
        dialog.resize(1280, 800)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_label = QLabel("")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title_label)

        image_label = QLabel("")
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setMinimumSize(640, 400)
        image_label.setStyleSheet("background: #000; border-radius: 8px;")
        layout.addWidget(image_label, 1)

        close_btn = QPushButton(t("close_button"))
        close_btn.clicked.connect(lambda: self._stop_slideshow())
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

        dialog.finished.connect(self._on_slideshow_dialog_closed)

        self._slideshow_dialog = dialog
        self._slideshow_image_label = image_label
        self._slideshow_title_label = title_label

    def _show_slideshow_entry(self, entry: GalleryEntry) -> None:
        self._ensure_slideshow_dialog()
        if self._slideshow_dialog is None or self._slideshow_image_label is None:
            return

        if not self._slideshow_dialog.isVisible():
            self._slideshow_dialog.show()

        self._slideshow_dialog.setWindowTitle(f"{t('gallery_slideshow_start')} - {entry.path.name}")
        if self._slideshow_title_label is not None:
            self._slideshow_title_label.setText(str(entry.path))

        pixmap = QPixmap(str(entry.path))
        if pixmap.isNull():
            self._slideshow_image_label.setText(t("preview_unavailable"))
            return

        target_size = self._slideshow_image_label.size()
        scaled = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._slideshow_image_label.setPixmap(scaled)

    def _on_slideshow_dialog_closed(self, *_args) -> None:
        self._stop_slideshow(close_dialog=False)
        self._slideshow_dialog = None
        self._slideshow_image_label = None
        self._slideshow_title_label = None

    # ──────────────────────────────────────────────────────────────────────────
    # Hilfsfunktionen
    # ──────────────────────────────────────────────────────────────────────────

    def _build_exif_snippet(self, entry: GalleryEntry) -> str:
        """Erstellt einen kurzen EXIF-Einzeiler (Datum + Kamera)."""
        parts = []

        # Datum aus capture_time
        if entry.capture_time:
            try:
                dt = datetime.fromtimestamp(entry.capture_time)
                parts.append(dt.strftime("%Y-%m-%d"))
            except (OSError, ValueError):
                pass

        # Kameramodell aus exif_json (wenn vorhanden)
        if entry.exif_json:
            import json
            try:
                exif = json.loads(entry.exif_json)
                model = exif.get("Model") or exif.get("Camera Model")
                if model:
                    model_str = str(model)
                    if len(model_str) > 20:
                        model_str = model_str[:18] + "…"
                    parts.append(model_str)
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        return " | ".join(parts)

    def _close_gallery(self):
        self._stop_slideshow()
        self.gallery_closed.emit()

    def retranslate(self):
        """Beschriftungen nach Sprachwechsel aktualisieren."""
        if hasattr(self, "_filter_bar"):
            self._filter_bar.retranslate()
        self._render_current_page()

    def closeEvent(self, event):
        """Ressourcen beim Schließen freigeben."""
        self._stop_slideshow()
        if self._thumb_loader.isRunning():
            self._thumb_loader.stop()
            self._thumb_loader.wait(2000)
        super().closeEvent(event)
