from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from photo_cleaner.config import AppConfig
from photo_cleaner.i18n import get_available_languages, get_language, t
from photo_cleaner.theme import get_theme


class FirstRunSetupDialog(QDialog):
    """Collect a small set of important first-run preferences."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(520)
        self.setWindowTitle(t("first_run_setup_title"))
        self._build_ui()
        self._load_defaults()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        self.setStyleSheet(
            "QGroupBox { font-weight: 600; border: 1px solid rgba(130,130,130,0.35); border-radius: 10px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
            "QLabel#first_run_muted { color: rgba(130,130,130,0.95); font-size: 12px; }"
            "QPushButton#first_run_primary { background: #2f6fde; color: white; border: none; border-radius: 8px; padding: 8px 14px; font-weight: 600; }"
            "QPushButton#first_run_primary:hover { background: #275ec1; }"
            "QPushButton#first_run_secondary { border-radius: 8px; padding: 8px 14px; }"
        )

        title = QLabel(f"<h2>{t('first_run_setup_title')}</h2>")
        layout.addWidget(title)

        subtitle = QLabel(t("first_run_setup_subtitle"))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        intro = QFrame()
        intro.setStyleSheet(
            "QFrame {"
            "background: rgba(47, 111, 222, 0.08);"
            "border: 1px solid rgba(47, 111, 222, 0.24);"
            "border-radius: 12px;"
            "}"
        )
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(14, 12, 14, 12)
        intro_layout.setSpacing(6)
        intro_label = QLabel(t("first_run_setup_intro"))
        intro_label.setWordWrap(True)
        intro_layout.addWidget(intro_label)
        layout.addWidget(intro)

        general_group = QGroupBox(t("settings_general_group"))
        general_layout = QVBoxLayout(general_group)
        general_layout.setSpacing(10)

        lang_row = QHBoxLayout()
        lang_label = QLabel(t("settings_language_label"))
        self.language_combo = QComboBox()
        for code, name in get_available_languages().items():
            self.language_combo.addItem(name, code)
        lang_row.addWidget(lang_label)
        lang_row.addWidget(self.language_combo, stretch=1)
        general_layout.addLayout(lang_row)

        theme_row = QHBoxLayout()
        theme_label = QLabel(t("settings_theme_label"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(t("theme_dark"), "dark")
        self.theme_combo.addItem(t("theme_light"), "light")
        theme_row.addWidget(theme_label)
        theme_row.addWidget(self.theme_combo, stretch=1)
        general_layout.addLayout(theme_row)

        layout.addWidget(general_group)

        behavior_group = QGroupBox(t("behavior_settings"))
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setSpacing(8)

        self.keep_originals_check = QCheckBox(t("keep_originals"))
        behavior_layout.addWidget(self.keep_originals_check)

        self.auto_backup_check = QCheckBox(t("auto_backup"))
        behavior_layout.addWidget(self.auto_backup_check)

        self.confirm_delete_check = QCheckBox(t("confirm_delete"))
        behavior_layout.addWidget(self.confirm_delete_check)

        delete_hint = QLabel(t("first_run_setup_delete_strategy_hint"))
        delete_hint.setObjectName("first_run_muted")
        delete_hint.setWordWrap(True)
        behavior_layout.addWidget(delete_hint)

        layout.addWidget(behavior_group)

        hint = QLabel(t("first_run_setup_settings_hint"))
        hint.setObjectName("first_run_muted")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignLeft)
        layout.addWidget(hint)

        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        skip_btn = QPushButton(t("first_run_setup_skip"))
        skip_btn.setObjectName("first_run_secondary")
        skip_btn.clicked.connect(self.reject)
        button_row.addWidget(skip_btn)

        continue_btn = QPushButton(t("first_run_setup_continue"))
        continue_btn.setObjectName("first_run_primary")
        continue_btn.setDefault(True)
        continue_btn.clicked.connect(self.accept)
        button_row.addWidget(continue_btn)

        layout.addLayout(button_row)

    def _load_defaults(self) -> None:
        settings = AppConfig.get_user_settings()
        dialog_settings = settings.get("settings_dialog", {})

        language = settings.get("language", get_language())
        lang_index = self.language_combo.findData(language)
        if lang_index >= 0:
            self.language_combo.setCurrentIndex(lang_index)

        theme = settings.get("theme", get_theme())
        theme_index = self.theme_combo.findData(theme)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)

        self.keep_originals_check.setChecked(bool(dialog_settings.get("keep_originals", True)))
        self.auto_backup_check.setChecked(bool(dialog_settings.get("auto_backup", True)))
        self.confirm_delete_check.setChecked(bool(dialog_settings.get("confirm_delete", True)))

    def selected_settings(self) -> dict[str, Any]:
        return {
            "language": self.language_combo.currentData() or get_language(),
            "theme": self.theme_combo.currentData() or get_theme(),
            "keep_originals": self.keep_originals_check.isChecked(),
            "auto_backup": self.auto_backup_check.isChecked(),
            "confirm_delete": self.confirm_delete_check.isChecked(),
        }