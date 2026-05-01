"""GalleryFilterBar — Filter-Leiste für die Gallery View.

Bietet:
- Zeitraum-Buttons: Alle / Heute / Diese Woche / Dieser Monat
- Score-Minimum-Slider
- Suchfeld (Dateiname / Pfad)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QWidget,
)

from photo_cleaner.ui.color_constants import get_semantic_colors
from photo_cleaner.theme import get_theme_colors
from photo_cleaner.i18n import t

logger = logging.getLogger(__name__)


@dataclass
class GalleryFilterOptions:
    search_text: str = ""
    min_score: int = 0          # 0–100
    date_from: Optional[date] = None
    date_to: Optional[date] = None

    @staticmethod
    def today() -> "GalleryFilterOptions":
        today = date.today()
        return GalleryFilterOptions(date_from=today, date_to=today)

    @staticmethod
    def this_week() -> "GalleryFilterOptions":
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        return GalleryFilterOptions(date_from=monday, date_to=today)

    @staticmethod
    def this_month() -> "GalleryFilterOptions":
        today = date.today()
        first = today.replace(day=1)
        return GalleryFilterOptions(date_from=first, date_to=today)


_PERIOD_BUTTONS = [
    ("all",   lambda: GalleryFilterOptions()),
    ("today", GalleryFilterOptions.today),
    ("week",  GalleryFilterOptions.this_week),
    ("month", GalleryFilterOptions.this_month),
]


def _btn_i18n_key(period_key: str) -> str:
    return {
        "all":   "gallery_filter_all",
        "today": "gallery_filter_today",
        "week":  "gallery_filter_week",
        "month": "gallery_filter_month",
    }[period_key]


class GalleryFilterBar(QWidget):
    """Horizontale Filter-Leiste oberhalb der Galerie."""

    filter_changed = Signal(object)  # GalleryFilterOptions

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_period = "all"
        self._period_btns: dict[str, QPushButton] = {}
        self._build_ui()

    # ──────────────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        colors = get_theme_colors()
        semantic = get_semantic_colors()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Zeitraum-Buttons
        for period_key, _ in _PERIOD_BUTTONS:
            btn = QPushButton(t(_btn_i18n_key(period_key)))
            btn.setCheckable(True)
            btn.setChecked(period_key == "all")
            btn.clicked.connect(lambda checked=False, pk=period_key: self._on_period_clicked(pk))
            btn.setMinimumHeight(28)
            self._period_btns[period_key] = btn
            layout.addWidget(btn)

        layout.addSpacing(12)

        # Score-Filter
        score_label = QLabel(t("gallery_filter_score"))
        score_label.setStyleSheet(f"font-size: 12px; color: {colors['text']};")
        layout.addWidget(score_label)

        self._score_slider = QSlider(Qt.Horizontal)
        self._score_slider.setRange(0, 100)
        self._score_slider.setValue(0)
        self._score_slider.setFixedWidth(100)
        self._score_slider.setTickPosition(QSlider.TicksBelow)
        self._score_slider.setTickInterval(25)
        self._score_slider.valueChanged.connect(self._on_filter_changed)
        layout.addWidget(self._score_slider)

        self._score_value_label = QLabel("0%")
        self._score_value_label.setStyleSheet(f"font-size: 11px; color: {colors['text']};")
        self._score_slider.valueChanged.connect(
            lambda v: self._score_value_label.setText(f"{v}%")
        )
        layout.addWidget(self._score_value_label)

        layout.addSpacing(12)

        # Suchfeld
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText(t("search_placeholder"))
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setMinimumHeight(28)
        self._search_box.setMaximumWidth(220)
        self._search_box.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self._search_box)

        layout.addStretch()

        self._apply_button_styles()

    def _apply_button_styles(self):
        colors = get_theme_colors()
        semantic = get_semantic_colors()
        for period_key, btn in self._period_btns.items():
            if period_key == self._active_period:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {semantic['info']}; color: white; "
                    "font-weight: bold; padding: 4px 12px; border-radius: 6px; border: none; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {colors['button']}; color: {colors['button_text']}; "
                    f"padding: 4px 12px; border-radius: 6px; border: 1px solid {colors['border']}; }}"
                    f"QPushButton:hover {{ background-color: {colors['alternate_base']}; }}"
                )

    # ──────────────────────────────────────────────────────────────────────────
    # Logik
    # ──────────────────────────────────────────────────────────────────────────

    def _on_period_clicked(self, period_key: str):
        self._active_period = period_key
        for pk, btn in self._period_btns.items():
            btn.setChecked(pk == period_key)
        self._apply_button_styles()
        self._on_filter_changed()

    def _on_filter_changed(self, *_):
        opts = self._build_filter()
        self.filter_changed.emit(opts)

    def _build_filter(self) -> GalleryFilterOptions:
        # Zeitraum-Basis
        for period_key, factory in _PERIOD_BUTTONS:
            if period_key == self._active_period:
                opts = factory()
                break
        else:
            opts = GalleryFilterOptions()

        opts.min_score = self._score_slider.value()
        opts.search_text = self._search_box.text().strip()
        return opts

    def reset(self):
        """Filter auf Standardwerte zurücksetzen."""
        self._active_period = "all"
        for pk, btn in self._period_btns.items():
            btn.setChecked(pk == "all")
        self._score_slider.setValue(0)
        self._search_box.clear()
        self._apply_button_styles()

    def retranslate(self):
        """Beschriftungen nach Sprachwechsel aktualisieren."""
        for period_key, btn in self._period_btns.items():
            btn.setText(t(_btn_i18n_key(period_key)))
        self._search_box.setPlaceholderText(t("search_placeholder"))
