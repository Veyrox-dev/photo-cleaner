"""Language selection dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from photo_cleaner.i18n import t, get_available_languages, get_language, set_language, save_language_to_settings
from photo_cleaner.config import AppConfig


class LanguageDialog(QDialog):
    """Dialog for selecting the UI language."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("language_dialog_title"))
        self.setModal(True)
        self.setMinimumWidth(420)

        self._list = QListWidget()
        self._build_ui()
        self._load_languages()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel(f"<b>{t('language_dialog_title')}</b>")
        title.setWordWrap(True)
        layout.addWidget(title)

        desc = QLabel(t("language_dialog_desc"))
        desc.setWordWrap(True)
        desc.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(desc)

        self._list.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton(t("cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton(t("apply"))
        apply_btn.clicked.connect(self._apply_selection)
        btn_row.addWidget(apply_btn)

        layout.addLayout(btn_row)

    def _load_languages(self) -> None:
        current = get_language()
        languages = get_available_languages()
        for code, name in languages.items():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, code)
            self._list.addItem(item)
            if code == current:
                item.setSelected(True)

    def _apply_selection(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        code = item.data(Qt.UserRole)
        if not code:
            return
        set_language(code)
        save_language_to_settings(AppConfig.get_user_data_dir() / "settings.json", code)
        self.accept()
