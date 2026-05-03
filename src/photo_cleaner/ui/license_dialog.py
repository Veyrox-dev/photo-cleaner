"""License Management Dialog für PhotoCleaner.

Zeigt Lizenz-Status, erlaubt Eingabe von Lizenzschlüsseln
und Upgrade-Informationen.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QColor, QTextOption
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QTextEdit,
    QMessageBox,
    QDialogButtonBox,
    QTabWidget,
    QWidget,
    QScrollArea,
    QFrame,
    QApplication,
)

from photo_cleaner.license import (
    LicenseManager,
    LicenseType,
)
from photo_cleaner.i18n import t
from photo_cleaner.services.license_service import LicenseService

logger = logging.getLogger(__name__)


_LICENSE_KEY_ALLOWED_PATTERN = re.compile(r"^[A-Z0-9-]+$")
_LICENSE_KEY_MAX_LENGTH = 128


def _validate_license_key_input(license_key: str) -> tuple[bool, str | None]:
    """Validate user-entered license key before activation request."""
    if not license_key:
        return False, "output_required"

    if len(license_key) > _LICENSE_KEY_MAX_LENGTH:
        return False, "license_key_too_long"

    if "-" not in license_key or not _LICENSE_KEY_ALLOWED_PATTERN.fullmatch(license_key):
        return False, "license_key_invalid_format"

    return True, None


class LicenseDialog(QDialog):
    """Dialog zur Lizenz-Verwaltung."""

    def __init__(self, license_manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.license_service = LicenseService(license_manager)
        self.setWindowTitle(f"PhotoCleaner - {t('license_management')}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setStyleSheet(
            "QDialog { font-size: 12px; }"
            "QGroupBox { margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
            "QTabBar::tab { padding: 6px 12px; }"
            "QLabel { padding: 2px 0; }"
        )
        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        """Baut die UI auf."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Tabs für verschiedene Sektionen
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setUsesScrollButtons(True)
        tabs.addTab(self._wrap_tab(self._create_status_tab()), t("license_status_tab"))
        tabs.addTab(self._wrap_tab(self._create_activation_tab()), t("license_activate_tab"))
        tabs.addTab(self._wrap_tab(self._create_features_tab()), "Features")
        layout.addWidget(tabs)

        # OK Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton(t("close"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _wrap_tab(self, content: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(content)

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return tab

    def _create_status_tab(self) -> QWidget:
        """Status-Tab mit aktuellem Lizenz-Status."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Status-Info Box
        status_box = QGroupBox(t("license_status_tab"))
        status_layout = QVBoxLayout(status_box)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 11pt; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(250)
        self.details_text.setWordWrapMode(QTextOption.WordWrap)
        self.details_text.setStyleSheet("padding: 8px;")
        status_layout.addWidget(self.details_text)

        layout.addWidget(status_box)

        # Feature-Status
        feature_box = QGroupBox("Features")
        feature_layout = QVBoxLayout(feature_box)

        self.features_text = QTextEdit()
        self.features_text.setReadOnly(True)
        self.features_text.setMaximumHeight(200)
        self.features_text.setWordWrapMode(QTextOption.WordWrap)
        self.features_text.setStyleSheet("padding: 8px;")
        feature_layout.addWidget(self.features_text)

        layout.addWidget(feature_box)
        layout.addStretch()

        return widget

    def _create_activation_tab(self) -> QWidget:
        """Aktivierungs-Tab für Supabase-Lizenzschlüssel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Lizenzschlüssel-Input-Box
        input_box = QGroupBox(t("license_activate_tab"))
        input_layout = QVBoxLayout(input_box)

        label = QLabel(t("license_management"))
        label.setWordWrap(True)
        input_layout.addWidget(label)

        # Input field
        key_layout = QHBoxLayout()
        key_label = QLabel(t("license_key_label"))
        key_label.setMinimumWidth(80)
        key_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText(t("license_key_placeholder"))
        self.key_input.setAccessibleName(t("license_key_label"))
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        input_layout.addLayout(key_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        activate_btn = QPushButton(t("start"))
        activate_btn.setAccessibleName(t("start"))
        activate_btn.clicked.connect(self._activate_license_key)
        btn_layout.addWidget(activate_btn)

        remove_btn = QPushButton(f"✗ {t('close')}")
        remove_btn.setAccessibleName("Remove license")
        remove_btn.clicked.connect(self._remove_license)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        input_layout.addLayout(btn_layout)

        layout.addWidget(input_box)

        # Info-Box
        info_box = QGroupBox(t("license_online_licensing"))
        info_layout = QVBoxLayout(info_box)

        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setWordWrapMode(QTextOption.WordWrap)
        info_text.setStyleSheet("padding: 8px;")
        info_text.setText(t("license_online_info_html"))
        info_layout.addWidget(info_text)

        layout.addWidget(info_box)

        return widget

    def _create_features_tab(self) -> QWidget:
        """Features-Tab mit marktgerechter Plan-Übersicht."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Plan-Vergleichstabelle
        comparison_html = t("license_plan_comparison_html")
        
        # HTML-TextEdit für Tabelle
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(comparison_html)
        text_edit.setWordWrapMode(QTextOption.WordWrap)
        text_edit.setStyleSheet("padding: 8px;")
        layout.addWidget(text_edit)
        
        # Aktueller Plan Indikator
        current_plan_label = QLabel()
        current_plan_label.setWordWrap(True)
        self._update_current_plan_indicator(current_plan_label)
        layout.addWidget(current_plan_label)
        
        # Store reference for refresh
        self._features_tab_label = current_plan_label

        return widget
    
    def _update_current_plan_indicator(self, label: QLabel):
        """Update current plan indicator in features tab."""
        status = self.license_service.get_license_status()
        license_type = status.get("license_type", "FREE").upper()
        valid = status.get("valid", False)
        
        if not valid:
            label.setText(f'<p style="background: #333; padding: 10px; border-radius: 5px;"><b>{t("license_your_plan")}:</b> FREE ({t("license_plan_standard")})</p>')
        elif license_type == "PRO":
            label.setText(f'<p style="background: #2a2a2a; padding: 10px; border-radius: 5px;"><b>{t("license_your_plan")}:</b> PRO ({t("license_plan_active")})</p>')
        else:
            label.setText(f'<p style="background: #333; padding: 10px; border-radius: 5px;"><b>{t("license_your_plan")}:</b> {license_type}</p>')

    def refresh_status(self):
        """Aktualisiert Status-Anzeigen."""
        status = self.license_service.get_license_status()

        # Status-Label
        license_type = status.get("license_type", "FREE").upper()
        valid = status.get("valid", False)
        expires = status.get("expires_at") or "Unbegrenzt"

        # FIX: FREE-Mode ist ein gültiger Zustand, auch ohne aktivierte Lizenz
        if valid or license_type == "FREE":
            if license_type == "PRO":
                color = "#FF9800"  # Orange
                icon = ""
            else:  # FREE
                color = "#4CAF50"  # Green
                icon = ""
                # Show user-friendly message for FREE mode
                if not valid:
                    license_type = f"FREE ({t('license_basic_features')})"
        else:
            # Invalid license (corrupted, expired, machine mismatch)
            color = "#999"  # Gray
            icon = ""
            reason = status.get("reason", t("license_invalid"))
            license_type = f"{license_type} ({reason})"

        self.status_label.setText(
            f'<span style="color: {color}; font-size: 14pt;">{license_type}</span>'
        )

        # Details (vereinfacht fuer FREE-Mode, detailliert fuer PRO/invalid)
        original_license_type = status.get("license_type", "FREE").upper()
        
        if original_license_type == "FREE" and not valid:
            # FREE-Mode: Show simplified, user-friendly details
            details = t("license_free_details")
        else:
            # PRO or invalid license: Show technical details
            details = f"""
{t('license_label')}: {license_type}
{t('license_user')}: {status.get('user', t('license_not_assigned'))}
{t('license_machine_id')}: {status.get('machine_id_license', 'N/A')[:16]}...
{t('license_expires')}: {expires}
{t('license_signature')}: {t('license_valid') if status.get('signature_valid') else t('license_invalid')}
{t('license_machine')}: {t('license_correct') if status.get('machine_match') else t('license_mismatch')}
            """.strip()

        self.details_text.setText(details)

        # Features
        enabled_features = status.get("enabled_features", [])
        if enabled_features:
            features_text = "\n".join(enabled_features)
        else:
            features_text = t("license_no_premium_features")

        self.features_text.setText(features_text)

    def _activate_license_key(self):
        """Aktiviert einen Lizenzschlüssel über Supabase."""
        license_key = self.key_input.text().strip().upper()
        self.key_input.setText(license_key)

        is_valid_input, error_key = _validate_license_key_input(license_key)
        if not is_valid_input:
            QMessageBox.warning(
                self,
                t("license_confirm_activation"),
                t(error_key or "license_key_invalid_format"),
            )
            return

        if not self.license_service.is_cloud_configured():
            QMessageBox.critical(
                self,
                t("license_configuration"),
                t("license_supabase_not_configured"),
            )
            return

        try:
            success, message = self.license_service.activate_with_key(license_key)
            if success:
                QMessageBox.information(self, t("license_activate_success"), message or t("license_activate_success"))
                # BUG FIX: Live-Update des UI ohne Dialog-Neuöffnung
                self._live_refresh_ui()
            else:
                QMessageBox.warning(self, t("license_activate_failed"), message or t("license_activate_failed"))
        except (OSError, IOError, ValueError) as e:
            logger.error("Activation failed: %s", e, exc_info=True)
            QMessageBox.critical(self, t("error"), f"{t('error')}: {e}")
    
    def _live_refresh_ui(self):
        """Aktualisiert alle UI-Elemente sofort nach Lizenz-Aktivierung."""
        # Refresh Status-Tab
        self.refresh_status()
        
        # Refresh Features-Tab current plan indicator
        if hasattr(self, '_features_tab_label'):
            self._update_current_plan_indicator(self._features_tab_label)
        
        # Force UI repaint
        self.update()
        QApplication.processEvents()
        
        logger.info("License dialog UI refreshed after activation")

    def _remove_license(self):
        """Entfernt aktuelle Lizenz."""
        reply = QMessageBox.warning(
            self,
            t("license_confirm_activation"),
            t("license_remove_confirmation"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            if self.license_service.remove_license():
                QMessageBox.information(self, t("action_success"), t("license_removed_success"))
                self.refresh_status()
            else:
                QMessageBox.critical(self, t("error"), t("license_removed_failed"))


