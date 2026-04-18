"""GalleryCard — leichtgewichtige Karte für Gallery View.

Unterschied zu ThumbnailCard:
- Keine Checkbox (Gallery ist read-only, kein Batch-Select nötig)
- Hover zeigt EXIF-Snippet (Datum + Kamera)
- Rechtsklick-Kontextmenü: Status ändern, Ordner öffnen
- Größere Thumbnails (200×200 statt 160×160)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtWidgets import (
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from photo_cleaner.models.status import FileStatus
from photo_cleaner.ui.color_constants import (
    get_semantic_colors,
    get_status_colors,
    get_text_hint_color,
    to_rgba,
)
from photo_cleaner.theme import get_theme_colors
from photo_cleaner.i18n import t

try:
    from shiboken6 import isValid as _qt_is_valid
except ImportError:
    def _qt_is_valid(obj) -> bool:
        return obj is not None

logger = logging.getLogger(__name__)

CARD_THUMB_SIZE = 200
CARD_WIDTH = 220
CARD_HEIGHT = 260


def _best_text_color_for_bg(background_color: str) -> str:
    color = QColor(background_color)
    return "#111111" if color.lightness() > 165 else "#ffffff"


class GalleryCard(QWidget):
    """Karte für einen einzelnen KEEP-Eintrag in der Gallery."""

    clicked = Signal(int)                  # index des Bildes
    status_change_requested = Signal(int, object)  # (index, FileStatus)
    open_folder_requested = Signal(int)    # index

    def __init__(self, path: Path, index: int, quality_score: Optional[float] = None,
                 exif_snippet: str = "", parent=None):
        super().__init__(parent)
        self.path = path
        self.index = index
        self.quality_score = quality_score
        self.exif_snippet = exif_snippet   # z.B. "2025-08-14 | Sony A7IV"
        self._pixmap: Optional[QPixmap] = None
        self.setObjectName("gallery_card")
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._build_ui()

    # ──────────────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        colors = get_theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Thumbnail
        self.thumbnail = QLabel()
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.setFixedSize(CARD_THUMB_SIZE, CARD_THUMB_SIZE)
        self.thumbnail.setStyleSheet(
            f"background-color: {colors['alternate_base']}; "
            f"border-radius: 6px; border: 1px solid {colors['border']};"
        )
        placeholder = QPixmap(CARD_THUMB_SIZE, CARD_THUMB_SIZE)
        placeholder.fill(Qt.gray)
        self.thumbnail.setPixmap(placeholder)
        layout.addWidget(self.thumbnail)

        # Dateiname (gekürzt)
        name = self.path.name
        if len(name) > 26:
            name = name[:23] + "..."
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(f"font-size: 11px; color: {colors['text']};")
        layout.addWidget(self.name_label)

        # EXIF-Snippet (Datum / Kamera) — anfangs leer, wird nachgeladen
        self.exif_label = QLabel(self.exif_snippet or "")
        self.exif_label.setAlignment(Qt.AlignCenter)
        hint_color = get_text_hint_color()
        self.exif_label.setStyleSheet(f"font-size: 10px; color: {hint_color};")
        layout.addWidget(self.exif_label)

        # Qualitäts-Badge
        if self.quality_score is not None:
            score = self.quality_score
            quality_label = self._build_score_badge(score)
            layout.addWidget(quality_label)

        self._apply_card_style(hovered=False)

    def _build_score_badge(self, score: float) -> QLabel:
        semantic = get_semantic_colors()
        if score >= 70:
            color = semantic["success"]
            text = f"★ {score:.0f}%"
        elif score >= 40:
            color = semantic["warning"]
            text = f"~ {score:.0f}%"
        else:
            color = semantic["error"]
            text = f"↓ {score:.0f}%"
        text_color = _best_text_color_for_bg(color)
        badge = QLabel(text)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background-color: {color}; color: {text_color}; "
            "font-weight: bold; padding: 2px 6px; border-radius: 6px; font-size: 10px;"
        )
        return badge

    def _apply_card_style(self, hovered: bool):
        colors = get_theme_colors()
        if hovered:
            self.setStyleSheet(
                f"QWidget#gallery_card {{ background-color: {colors['alternate_base']}; "
                f"border-radius: 12px; border: 2px solid {colors['highlight']}; }}"
            )
        else:
            self.setStyleSheet(
                f"QWidget#gallery_card {{ background-color: {colors['base']}; "
                f"border-radius: 12px; border: 2px solid {colors['border']}; }}"
                f"QWidget#gallery_card:hover {{ background-color: {colors['alternate_base']}; "
                f"border-color: {colors['highlight']}; }}"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Interaktion
    # ──────────────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._apply_card_style(hovered=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_card_style(hovered=False)
        super().leaveEvent(event)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        status_colors = get_status_colors()

        keep_action = menu.addAction(t("keep"))
        keep_action.triggered.connect(
            lambda: self.status_change_requested.emit(self.index, FileStatus.KEEP)
        )

        del_action = menu.addAction(t("delete"))
        del_action.triggered.connect(
            lambda: self.status_change_requested.emit(self.index, FileStatus.DELETE)
        )

        unsure_action = menu.addAction(t("unsure"))
        unsure_action.triggered.connect(
            lambda: self.status_change_requested.emit(self.index, FileStatus.UNSURE)
        )

        menu.addSeparator()

        open_action = menu.addAction(t("open_folder"))
        open_action.triggered.connect(
            lambda: self.open_folder_requested.emit(self.index)
        )

        menu.exec(self.mapToGlobal(pos))

    # ──────────────────────────────────────────────────────────────────────────
    # Thumbnail (async)
    # ──────────────────────────────────────────────────────────────────────────

    def set_thumbnail_image(self, qimg: QImage) -> None:
        """Setzt QImage-Thumbnail (UI-Thread only)."""
        if not _qt_is_valid(self) or not _qt_is_valid(getattr(self, "thumbnail", None)):
            return
        if qimg.isNull():
            return
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            CARD_THUMB_SIZE, CARD_THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._pixmap = scaled
        try:
            self.thumbnail.setPixmap(scaled)
        except RuntimeError:
            pass

    def set_exif_snippet(self, text: str) -> None:
        self.exif_snippet = text
        if _qt_is_valid(getattr(self, "exif_label", None)):
            try:
                self.exif_label.setText(text)
            except RuntimeError:
                pass

    def cleanup(self):
        self._pixmap = None
        if _qt_is_valid(getattr(self, "thumbnail", None)):
            try:
                self.thumbnail.clear()
                self.thumbnail.setPixmap(QPixmap())
            except RuntimeError:
                pass
        self.thumbnail = None
