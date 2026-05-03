from __future__ import annotations

import time
from collections import deque
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from photo_cleaner.i18n import t
from photo_cleaner.theme import get_theme_colors
from photo_cleaner.ui.color_constants import get_semantic_colors


class ProgressStepDialog(QDialog):
    """Phase D: Enhanced progress dialog with step indicators and ETA."""

    cancelled = Signal()

    def __init__(
        self,
        parent=None,
        *,
        window_title: str | None = None,
        step_names: Optional[List[str]] = None,
        show_sub_progress: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(window_title or t("image_analysis"))
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.current_step = 0
        self.step_names = step_names or [
            t("progress_step_1_scanning"),
            t("progress_step_2_grouping"),
            t("progress_step_3_rating"),
            t("progress_step_4_finalization"),
        ]
        self.step_count = len(self.step_names)
        self._show_sub_progress = show_sub_progress
        self.start_time = time.time()
        self.last_update_time = 0
        self.last_percentage = 0
        self._eta_points: deque[tuple[float, int]] = deque(maxlen=24)
        self._smoothed_eta_seconds: float | None = None
        self._last_activity_entry: str = ""
        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self):
        """Setup dialog UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.step_label = QLabel()
        step_font = self.step_label.font()
        step_font.setPointSize(12)
        step_font.setBold(True)
        self.step_label.setFont(step_font)
        layout.addWidget(self.step_label)

        milestones_layout = QHBoxLayout()
        milestones_layout.setSpacing(10)
        self.step_progress_bars: list[QProgressBar] = []
        for name in self.step_names:
            step_column = QVBoxLayout()
            step_column.setSpacing(4)

            step_name = QLabel(name.replace("...", ""))
            step_name.setAlignment(Qt.AlignCenter)
            step_name.setStyleSheet("font-size: 12px;")

            mini_bar = QProgressBar()
            mini_bar.setMinimum(0)
            mini_bar.setMaximum(100)
            mini_bar.setValue(0)
            mini_bar.setTextVisible(False)
            mini_bar.setFixedHeight(8)

            step_column.addWidget(step_name)
            step_column.addWidget(mini_bar)
            milestones_layout.addLayout(step_column)
            self.step_progress_bars.append(mini_bar)

        layout.addLayout(milestones_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.sub_status_label = QLabel("")
        self.sub_status_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.sub_status_label)

        self.sub_progress_bar = QProgressBar()
        self.sub_progress_bar.setMinimum(0)
        self.sub_progress_bar.setMaximum(100)
        self.sub_progress_bar.setValue(0)
        self.sub_progress_bar.setTextVisible(True)
        self.sub_progress_bar.setFixedHeight(16)
        layout.addWidget(self.sub_progress_bar)

        if not self._show_sub_progress:
            self.sub_status_label.hide()
            self.sub_progress_bar.hide()

        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)
        self.status_label = QLabel()
        info_layout.addWidget(self.status_label)
        self.eta_label = QLabel()
        info_layout.addStretch()
        info_layout.addWidget(self.eta_label)
        layout.addLayout(info_layout)

        self.activity_label = QLabel(t("analysis_activity_title"))
        self.activity_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(self.activity_label)

        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMinimumHeight(90)
        self.activity_log.setMaximumHeight(140)
        self.activity_log.setStyleSheet("QTextEdit { font-size: 12px; }")
        layout.addWidget(self.activity_log)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton(t("cancel"))
        cancel_btn.setAccessibleName(t("cancel"))
        cancel_btn.clicked.connect(self.cancelled.emit)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self._update_step_visuals()
        self.append_activity_log(t("analysis_activity_ready"))

    def _apply_styling(self):
        """Apply Phase C consistent styling."""
        colors = get_semantic_colors()
        theme_colors = get_theme_colors()

        bg_color = theme_colors.get("base", "#ffffff")
        progress_color = colors["info"]

        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid {colors['neutral']};
                border-radius: 4px;
                background-color: {bg_color};
                text-align: center;
                min-height: 24px;
            }}
            QProgressBar::chunk {{
                background-color: {progress_color};
                border-radius: 3px;
            }}
        """
        )

        self.sub_progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid {colors['neutral']};
                border-radius: 4px;
                background-color: {bg_color};
                text-align: center;
                min-height: 16px;
                font-size: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {colors['info']};
                border-radius: 3px;
            }}
        """
        )

        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {theme_colors.get('window', '#f5f5f5')};
                color: {theme_colors.get('text', '#000000')};
            }}
        """
        )

    def set_step(self, step: int):
        """Update current step (1-4)."""
        self.current_step = max(0, min(step, self.step_count))
        self._update_step_label()
        self._update_step_visuals()

    def _set_milestone_state(self, bar: QProgressBar, state: str) -> None:
        colors = get_theme_colors()
        semantic = get_semantic_colors()
        border = colors.get("border", "#7f8c8d")
        pending_bg = colors.get("alternate_base", "#d0d3d6")
        base_bg = colors.get("base", "#d9dde1")

        if state == "done":
            bar.setRange(0, 100)
            bar.setValue(100)
            bar.setStyleSheet(
                f"QProgressBar {{ border: 1px solid {border}; border-radius: 4px; background-color: {base_bg}; }}"
                f"QProgressBar::chunk {{ background-color: {semantic['success']}; border-radius: 3px; }}"
            )
            return

        if state == "active":
            bar.setRange(0, 0)
            bar.setStyleSheet(
                f"QProgressBar {{ border: 1px solid {border}; border-radius: 4px; background-color: {base_bg}; }}"
                f"QProgressBar::chunk {{ background-color: {semantic['info']}; border-radius: 3px; }}"
            )
            return

        bar.setRange(0, 100)
        bar.setValue(100)
        bar.setStyleSheet(
            f"QProgressBar {{ border: 1px solid {border}; border-radius: 4px; background-color: {pending_bg}; }}"
            f"QProgressBar::chunk {{ background-color: {pending_bg}; border-radius: 3px; }}"
        )

    def _update_step_visuals(self) -> None:
        if not self.step_progress_bars:
            return

        active_idx = self.current_step - 1 if self.current_step > 0 else 0
        for idx, bar in enumerate(self.step_progress_bars):
            if idx < active_idx:
                self._set_milestone_state(bar, "done")
            elif idx == active_idx:
                self._set_milestone_state(bar, "active")
            else:
                self._set_milestone_state(bar, "pending")

        self._update_step_label()

    def _update_step_label(self):
        if self.current_step <= 0:
            text = t("progress_step_initializing")
        else:
            idx = max(0, min(self.current_step - 1, self.step_count - 1))
            step_name = self.step_names[idx]
            text = t("progress_step_label").format(current=self.current_step, total=self.step_count, step_name=step_name)

        self.step_label.setText(text)

    def append_activity_log(self, message: str) -> None:
        message = (message or "").strip()
        if not message:
            return
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        if entry == self._last_activity_entry:
            return
        self._last_activity_entry = entry
        self.activity_log.append(entry)
        scrollbar = self.activity_log.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def set_sub_progress(self, value: int, status_text: str | None = None) -> None:
        if not self._show_sub_progress:
            return
        value = max(0, min(100, int(value)))
        self.sub_progress_bar.setValue(value)
        if status_text is not None:
            text = status_text.strip()
            self.sub_status_label.setText(text)
            if text:
                self.append_activity_log(text)

    def _update_eta(self, percentage: int):
        elapsed = time.time() - self.start_time

        if percentage <= 0:
            self.eta_label.setText("ETA: --")
            return

        now = time.time()
        self._eta_points.append((now, percentage))

        eta_seconds = None
        if len(self._eta_points) >= 2:
            oldest_t, oldest_p = self._eta_points[0]
            newest_t, newest_p = self._eta_points[-1]
            delta_p = newest_p - oldest_p
            delta_t = newest_t - oldest_t
            if delta_p > 0 and delta_t > 0:
                speed = delta_p / delta_t
                remaining = max(0, 100 - percentage)
                eta_seconds = remaining / speed

        if eta_seconds is None:
            eta_seconds = (elapsed / percentage) * (100 - percentage)

        if self._smoothed_eta_seconds is None:
            self._smoothed_eta_seconds = eta_seconds
        else:
            self._smoothed_eta_seconds = (0.7 * self._smoothed_eta_seconds) + (0.3 * eta_seconds)

        eta = max(0, int(self._smoothed_eta_seconds))

        if eta < 60:
            eta_text = f"ETA: {eta}s"
        else:
            mins = eta // 60
            secs = eta % 60
            eta_text = f"ETA: {mins}:{secs:02d}"

        self.eta_label.setText(eta_text)

    def set_status_text(self, text: str):
        self.status_label.setText(text)

    def set_progress(self, value: int):
        self.progress_bar.setValue(value)
        self.last_percentage = value
        self.last_update_time = time.time()
        self._update_eta(value)

    def closeEvent(self, event):
        self.cancelled.emit()
        super().closeEvent(event)

    def setMinimum(self, value: int):
        self.progress_bar.setMinimum(value)

    def setMaximum(self, value: int):
        self.progress_bar.setMaximum(value)

    def setValue(self, value: int):
        self.progress_bar.setValue(value)
        self.last_percentage = value
        self.last_update_time = time.time()
        self._update_eta(value)

    def setLabelText(self, text: str):
        self.status_label.setText(text)

    def setFormat(self, text: str):
        self.progress_bar.setFormat(text)


class FinalizationResultDialog(QDialog):
    """Phase D: Custom completion dialog with user-relevant results only."""

    report_error = Signal()

    def __init__(
        self,
        total_files: int,
        groups_found: int,
        new_files: int,
        cached_files: int,
        error_files: List[str] = None,
        analysis_time: float = 0,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(t("finalization_dialog_title"))
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)

        self.total_files = total_files
        self.groups_found = groups_found
        self.new_files = new_files
        self.cached_files = cached_files
        self.error_files = error_files or []
        self.analysis_time = analysis_time

        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self):
        """Setup dialog UI components."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        summary_card = self._create_summary_card()
        main_layout.addWidget(summary_card)

        if self.error_files:
            error_card = self._create_error_card()
            main_layout.addWidget(error_card)

        info_card = self._create_info_card()
        main_layout.addWidget(info_card)

        main_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        if self.error_files:
            report_btn = QPushButton(t("finalization_button_report_error"))
            report_btn.setAccessibleName(t("finalization_button_report_error"))
            report_btn.clicked.connect(self.report_error.emit)
            button_layout.addWidget(report_btn)

        ok_btn = QPushButton(t("finalization_button_ok"))
        ok_btn.setAccessibleName(t("finalization_button_ok"))
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def _create_summary_card(self) -> QWidget:
        card = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title_label = QLabel(
            t("finalization_success_summary").format(total=self.total_files, groups=self.groups_found)
        )
        title_font = title_label.font()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        colors = get_semantic_colors()

        card.setLayout(layout)
        self._apply_card_styling(card, colors["success"])

        return card

    def _create_error_card(self) -> QWidget:
        card = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        colors = get_semantic_colors()

        error_count = len(self.error_files)
        error_title = QLabel(t("finalization_errors_header"))
        error_title_font = error_title.font()
        error_title_font.setBold(True)
        error_title.setFont(error_title_font)
        error_title.setStyleSheet(f"color: {colors['error']};")
        layout.addWidget(error_title)

        error_msg = QLabel(t("finalization_error_loading").format(count=error_count))
        error_msg.setStyleSheet(f"color: {colors['error']};")
        layout.addWidget(error_msg)

        if self.error_files:
            files_label = QLabel(t("finalization_affected_files") + ":")
            files_label_font = files_label.font()
            files_label_font.setBold(True)
            files_label.setFont(files_label_font)
            layout.addWidget(files_label)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            file_list_widget = QWidget()
            file_list_layout = QVBoxLayout()
            file_list_layout.setContentsMargins(0, 0, 0, 0)
            file_list_layout.setSpacing(4)

            for file_path in self.error_files[:20]:
                file_item = QLabel(f"• {file_path}")
                file_item.setWordWrap(True)
                file_list_layout.addWidget(file_item)

            if len(self.error_files) > 20:
                more_label = QLabel(f"... und {len(self.error_files) - 20} weitere")
                more_label.setStyleSheet(f"color: {colors['neutral']};")
                file_list_layout.addWidget(more_label)

            file_list_layout.addStretch()
            file_list_widget.setLayout(file_list_layout)
            scroll.setWidget(file_list_widget)
            scroll.setMaximumHeight(150)
            layout.addWidget(scroll)

        card.setLayout(layout)
        self._apply_card_styling(card, colors["error"])

        return card

    def _create_info_card(self) -> QWidget:
        card = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        colors = get_semantic_colors()

        info_text = t("finalization_processing_info").format(new=self.new_files, cached=self.cached_files)
        info_label = QLabel(info_text)
        layout.addWidget(info_label)

        if self.analysis_time > 0:
            minutes = int(self.analysis_time // 60)
            seconds = int(self.analysis_time % 60)
            time_label = QLabel(f"Analysezeit: {minutes}:{seconds:02d}")
            layout.addWidget(time_label)

        card.setLayout(layout)
        theme_colors = get_theme_colors()
        bg_color = theme_colors.get("alternate_base", theme_colors.get("base", "#f5f5f5"))
        text_color = theme_colors.get("text", "#000000")
        card.setStyleSheet(
            f"""
            QWidget {{
                background-color: {bg_color};
                border: 1px solid {colors['neutral']};
                border-radius: 6px;
                color: {text_color};
            }}
        """
        )

        return card

    def _apply_card_styling(self, card: QWidget, accent_color: str):
        bg_color = get_theme_colors().get("base", "#ffffff")

        card.setStyleSheet(
            f"""
            QWidget {{
                background-color: {bg_color};
                border: 2px solid {accent_color};
                border-radius: 6px;
                padding: 0px;
            }}
        """
        )

    def _apply_styling(self):
        theme_colors = get_theme_colors()
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {theme_colors.get('window', '#f5f5f5')};
                color: {theme_colors.get('text', '#000000')};
            }}
            QPushButton {{
                min-height: 36px;
                min-width: 80px;
                border-radius: 4px;
                padding: 0px 16px;
                font-size: 13px;
                font-weight: bold;
                background-color: {get_semantic_colors()['info']};
                color: white;
                border: none;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                opacity: 0.8;
            }}
        """
        )
