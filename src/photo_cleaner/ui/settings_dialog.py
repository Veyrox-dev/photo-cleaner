"""Comprehensive settings dialog for PhotoCleaner."""

import logging
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSpinBox, QSlider, QCheckBox, QComboBox,
    QPushButton, QGroupBox, QScrollArea, QMessageBox, QFileDialog, QFrame,
    QTextBrowser
)
from PySide6.QtCore import Qt, QSize, QEvent, QUrl
from photo_cleaner.i18n import t, get_available_languages, get_language
from photo_cleaner.theme import get_theme
from photo_cleaner.config import AppConfig

logger = logging.getLogger(__name__)


class LegalDocumentDialog(QDialog):
    """Display legal HTML content in an in-app dialog."""

    def __init__(self, title: str, html_content: str, base_url: QUrl, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 760)
        self.setMinimumSize(720, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        browser = QTextBrowser(self)
        browser.setOpenExternalLinks(True)
        browser.setHtml(html_content)
        if base_url.isValid():
            browser.document().setBaseUrl(base_url)
        layout.addWidget(browser)

        close_btn = QPushButton(t("close"))
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


class SettingsDialog(QDialog):
    """Comprehensive settings dialog for PhotoCleaner."""
    
    def __init__(self, parent=None, actions=None):
        super().__init__(parent)
        
        self.setWindowTitle(t("settings_title"))
        self.resize(600, 700)
        self.setMinimumWidth(640)
        self.setMinimumHeight(720)
        self.setModal(True)
        self.setStyleSheet(
            "QDialog { font-size: 12px; }"
            "QGroupBox { margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
            "QTabBar::tab { padding: 6px 12px; }"
            "QLabel { padding: 2px 0; }"
            "QCheckBox { padding: 2px 0; }"
            "QPushButton { background-color: #2f6fde; color: #ffffff; border: 1px solid #2256b3; padding: 8px 14px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #2b63c8; }"
            "QPushButton:disabled { background-color: #8aa7e0; color: #e9eef9; border: 1px solid #7b96cc; }"
            "QSlider::groove:horizontal { height: 6px; background: #d7e2f8; border-radius: 3px; }"
            "QSlider::sub-page:horizontal { background: #2f6fde; border-radius: 3px; }"
            "QSlider::add-page:horizontal { background: #d7e2f8; border-radius: 3px; }"
            "QSlider::handle:horizontal { width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; background: #2f6fde; border: 1px solid #2256b3; }"
        )
        
        # QUICK-WIN #4: Track signal connections for cleanup on close
        self._signal_connections = []  # List of (signal, slot) tuples to disconnect
        
        # Import systems
        try:
            from photo_cleaner.config_update_system import get_config_update_system, ChangeType
            from photo_cleaner.preset_manager import get_preset_manager
            self.config_system = get_config_update_system()
            self.preset_manager = get_preset_manager()
            self.change_type = ChangeType
        except ImportError as e:
            logger.warning(f"Could not import config systems: {e}")
            self.config_system = None
            self.preset_manager = None

        # Optional actions for maintenance operations
        self.actions = actions
        
        self._build_ui()
        self._load_settings()
    
    def _connect_signal(self, signal, slot):
        """Connect signal and track for cleanup (QUICK-WIN #4)."""
        signal.connect(slot)
        self._signal_connections.append((signal, slot))
    
    def _build_ui(self):
        """Build settings UI with tabs."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Add title
        title = QLabel(f"<h2>{t('settings_title')}</h2>")
        title.setWordWrap(True)
        layout.addWidget(title)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setUsesScrollButtons(True)
        
        # Reduced tab layout with system settings first.
        self.tabs.addTab(self._build_maintenance_tab(), t("settings_tab_system"))
        self.tabs.addTab(self._build_quality_tab(), t("settings_tab_analysis"))
        self.tabs.addTab(self._build_output_tab(), t("settings_tab_workflow"))
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        reset_btn = QPushButton(t("reset_settings"))
        reset_btn.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        cancel_btn = QPushButton(t("cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton(f"{t('save_settings')}")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _build_quality_tab(self) -> QWidget:
        """Build quality settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Presets
        preset_group = QGroupBox(t("presets"))
        preset_layout = QVBoxLayout(preset_group)
        
        preset_layout.addWidget(self._make_label(t("preset_quality_profiles")))
        
        self.preset_combo = QComboBox()
        self._install_no_wheel(self.preset_combo)
        if self.preset_manager:
            presets = self.preset_manager.list_presets()
            self.preset_combo.addItems(presets)
        self._connect_signal(self.preset_combo.currentTextChanged, self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo)
        
        layout.addWidget(preset_group)
        
        # Quality weights
        quality_group = QGroupBox(t("quality_weights"))
        quality_layout = QVBoxLayout(quality_group)
        quality_layout.setSpacing(12)
        
        # Blur weight
        blur_row = QHBoxLayout()
        blur_row.addWidget(self._make_field_label(f"{t('blur')}"))
        self.blur_slider = QSlider(Qt.Horizontal)
        self._install_no_wheel(self.blur_slider)
        self.blur_slider.setMinimum(0)
        self.blur_slider.setMaximum(100)
        self.blur_value_label = QLabel("50%")
        self._connect_signal(self.blur_slider.valueChanged, lambda v: self.blur_value_label.setText(f"{v}%"))
        blur_row.addWidget(self.blur_slider, stretch=1)
        blur_row.addWidget(self.blur_value_label, stretch=0)
        quality_layout.addLayout(blur_row)
        
        # Contrast weight
        contrast_row = QHBoxLayout()
        contrast_row.addWidget(self._make_field_label(f"{t('contrast')}"))
        self.contrast_slider = QSlider(Qt.Horizontal)
        self._install_no_wheel(self.contrast_slider)
        self.contrast_slider.setMinimum(0)
        self.contrast_slider.setMaximum(100)
        self.contrast_value_label = QLabel("50%")
        self._connect_signal(self.contrast_slider.valueChanged, lambda v: self.contrast_value_label.setText(f"{v}%"))
        contrast_row.addWidget(self.contrast_slider, stretch=1)
        contrast_row.addWidget(self.contrast_value_label, stretch=0)
        quality_layout.addLayout(contrast_row)
        
        # Exposure weight
        exposure_row = QHBoxLayout()
        exposure_row.addWidget(self._make_field_label(f"{t('exposure')}"))
        self.exposure_slider = QSlider(Qt.Horizontal)
        self._install_no_wheel(self.exposure_slider)
        self.exposure_slider.setMinimum(0)
        self.exposure_slider.setMaximum(100)
        self.exposure_value_label = QLabel("50%")
        self._connect_signal(self.exposure_slider.valueChanged, lambda v: self.exposure_value_label.setText(f"{v}%"))
        exposure_row.addWidget(self.exposure_slider, stretch=1)
        exposure_row.addWidget(self.exposure_value_label, stretch=0)
        quality_layout.addLayout(exposure_row)
        
        # Noise weight
        noise_row = QHBoxLayout()
        noise_row.addWidget(self._make_field_label(f"{t('noise')}"))
        self.noise_slider = QSlider(Qt.Horizontal)
        self._install_no_wheel(self.noise_slider)
        self.noise_slider.setMinimum(0)
        self.noise_slider.setMaximum(100)
        self.noise_value_label = QLabel("50%")
        self._connect_signal(self.noise_slider.valueChanged, lambda v: self.noise_value_label.setText(f"{v}%"))
        noise_row.addWidget(self.noise_slider, stretch=1)
        noise_row.addWidget(self.noise_value_label, stretch=0)
        quality_layout.addLayout(noise_row)
        
        layout.addWidget(quality_group)

        # Detection Settings
        detection_group = QGroupBox(t("detection_tab"))
        detection_layout = QVBoxLayout(detection_group)
        detection_layout.setSpacing(8)

        self.closed_eyes_check = QCheckBox(t("closed_eyes_detection"))
        detection_layout.addWidget(self.closed_eyes_check)

        self.redeye_check = QCheckBox(t("redeye_detection"))
        detection_layout.addWidget(self.redeye_check)

        self.blurry_check = QCheckBox(t("blurry_detection"))
        detection_layout.addWidget(self.blurry_check)

        self.underexposed_check = QCheckBox(t("underexposed_detection"))
        detection_layout.addWidget(self.underexposed_check)

        self.overexposed_check = QCheckBox(t("overexposed_detection"))
        detection_layout.addWidget(self.overexposed_check)

        layout.addWidget(detection_group)

        # Duplicate grouping behavior
        grouping_group = QGroupBox(t("duplicate_groups"))
        grouping_layout = QVBoxLayout(grouping_group)
        grouping_layout.setSpacing(8)

        grouping_layout.addWidget(self._make_label(t("similarity_threshold")))
        self.similarity_spin = QSpinBox()
        self._install_no_wheel(self.similarity_spin)
        self.similarity_spin.setMinimum(1)
        self.similarity_spin.setMaximum(100)
        self.similarity_spin.setValue(85)
        self.similarity_spin.setSuffix("%")
        grouping_layout.addWidget(self.similarity_spin)

        self.show_advanced_check = QCheckBox(t("settings_show_advanced"))
        grouping_layout.addWidget(self.show_advanced_check)

        self.advanced_group = QGroupBox(t("settings_advanced_group"))
        advanced_layout = QVBoxLayout(self.advanced_group)
        advanced_layout.setSpacing(8)

        window_row = QHBoxLayout()
        window_row.addWidget(self._make_field_label(t("settings_group_time_window")))
        self.group_time_window_spin = QSpinBox()
        self._install_no_wheel(self.group_time_window_spin)
        self.group_time_window_spin.setMinimum(0)
        self.group_time_window_spin.setMaximum(600)
        self.group_time_window_spin.setSuffix(" s")
        window_row.addWidget(self.group_time_window_spin)
        window_row.addStretch()
        advanced_layout.addLayout(window_row)

        relaxed_row = QHBoxLayout()
        relaxed_row.addWidget(self._make_field_label(t("settings_group_relaxed_similarity")))
        self.group_relaxed_similarity_spin = QSpinBox()
        self._install_no_wheel(self.group_relaxed_similarity_spin)
        self.group_relaxed_similarity_spin.setMinimum(40)
        self.group_relaxed_similarity_spin.setMaximum(100)
        self.group_relaxed_similarity_spin.setSuffix("%")
        relaxed_row.addWidget(self.group_relaxed_similarity_spin)
        relaxed_row.addStretch()
        advanced_layout.addLayout(relaxed_row)

        self.advanced_group.setVisible(False)
        self._connect_signal(self.show_advanced_check.toggled, self.advanced_group.setVisible)
        grouping_layout.addWidget(self.advanced_group)

        layout.addWidget(grouping_group)
        layout.addStretch()
        
        return self._wrap_tab(content)
    
    def _build_output_tab(self) -> QWidget:
        """Build output settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Export format
        export_group = QGroupBox(f"{t('export_tab')}")
        export_layout = QVBoxLayout(export_group)
        
        export_layout.addWidget(self._make_label(t("export_format")))
        self.export_format_combo = QComboBox()
        self._install_no_wheel(self.export_format_combo)
        self.export_format_combo.addItem(t("export_format_original"), "original")
        self.export_format_combo.addItem(t("export_format_jpg"), "jpg")
        self.export_format_combo.addItem(t("export_format_png"), "png")
        self.export_format_combo.addItem(t("export_format_webp"), "webp")
        self.export_format_combo.addItem(t("export_format_tiff"), "tiff")
        self.export_format_combo.addItem(t("export_format_bmp"), "bmp")
        export_layout.addWidget(self.export_format_combo)

        # Export structure (folder layout)
        export_layout.addWidget(self._make_label(t("export_structure_label")))
        self.export_structure_combo = QComboBox()
        self._install_no_wheel(self.export_structure_combo)
        self._export_structure_codes = ("date", "year_month", "year", "month_day", "month", "flat")
        self.export_structure_combo.addItem(t("export_structure_date"),      "date")
        self.export_structure_combo.addItem(t("export_structure_year_month"), "year_month")
        self.export_structure_combo.addItem(t("export_structure_year"),       "year")
        self.export_structure_combo.addItem(t("export_structure_month_day"),  "month_day")
        self.export_structure_combo.addItem(t("export_structure_month"),      "month")
        self.export_structure_combo.addItem(t("export_structure_flat"),       "flat")
        export_layout.addWidget(self.export_structure_combo)

        auto_keep_group = QGroupBox(t("auto_keep_tiers_title"))
        auto_keep_layout = QVBoxLayout(auto_keep_group)
        auto_keep_layout.setSpacing(6)

        # Tier 1: small groups
        tier1_row = QHBoxLayout()
        tier1_row.addWidget(self._make_field_label(t("auto_keep_tiers_row_prefix")))
        self.tier1_threshold_spin = QSpinBox()
        self._install_no_wheel(self.tier1_threshold_spin)
        self.tier1_threshold_spin.setMinimum(1)
        self.tier1_threshold_spin.setMaximum(200)
        tier1_row.addWidget(self.tier1_threshold_spin)
        tier1_row.addWidget(self._make_field_label(t("auto_keep_tiers_row_middle")))
        self.tier1_keep_spin = QSpinBox()
        self._install_no_wheel(self.tier1_keep_spin)
        self.tier1_keep_spin.setMinimum(0)
        self.tier1_keep_spin.setMaximum(20)
        tier1_row.addWidget(self.tier1_keep_spin)
        tier1_row.addStretch()
        auto_keep_layout.addLayout(tier1_row)

        # Tier 2: medium groups
        tier2_row = QHBoxLayout()
        tier2_row.addWidget(self._make_field_label(t("auto_keep_tiers_row_prefix")))
        self.tier2_threshold_spin = QSpinBox()
        self._install_no_wheel(self.tier2_threshold_spin)
        self.tier2_threshold_spin.setMinimum(1)
        self.tier2_threshold_spin.setMaximum(200)
        tier2_row.addWidget(self.tier2_threshold_spin)
        tier2_row.addWidget(self._make_field_label(t("auto_keep_tiers_row_middle")))
        self.tier2_keep_spin = QSpinBox()
        self._install_no_wheel(self.tier2_keep_spin)
        self.tier2_keep_spin.setMinimum(0)
        self.tier2_keep_spin.setMaximum(20)
        tier2_row.addWidget(self.tier2_keep_spin)
        tier2_row.addStretch()
        auto_keep_layout.addLayout(tier2_row)

        # Tier 3: large groups
        tier3_row = QHBoxLayout()
        tier3_row.addWidget(self._make_field_label(t("auto_keep_tiers_large_prefix")))
        self.tier3_keep_spin = QSpinBox()
        self._install_no_wheel(self.tier3_keep_spin)
        self.tier3_keep_spin.setMinimum(0)
        self.tier3_keep_spin.setMaximum(20)
        tier3_row.addWidget(self.tier3_keep_spin)
        tier3_row.addStretch()
        auto_keep_layout.addLayout(tier3_row)

        export_layout.addWidget(auto_keep_group)
        
        # Quality for conversion
        quality_row = QHBoxLayout()
        quality_row.addWidget(self._make_field_label(t("compression_quality")))
        self.export_quality_spin = QSpinBox()
        self._install_no_wheel(self.export_quality_spin)
        self.export_quality_spin.setMinimum(50)
        self.export_quality_spin.setMaximum(100)
        self.export_quality_spin.setValue(100)
        self.export_quality_spin.setSuffix("%")
        quality_row.addWidget(self.export_quality_spin)
        quality_row.addStretch()
        export_layout.addLayout(quality_row)
        
        layout.addWidget(export_group)
        
        # Behavior settings
        behavior_group = QGroupBox(t("behavior_settings"))
        behavior_layout = QVBoxLayout(behavior_group)
        
        self.keep_originals_check = QCheckBox(t("keep_originals"))
        self.keep_originals_check.setChecked(True)
        behavior_layout.addWidget(self.keep_originals_check)
        
        self.auto_backup_check = QCheckBox(t("auto_backup"))
        self.auto_backup_check.setChecked(True)
        behavior_layout.addWidget(self.auto_backup_check)
        
        self.confirm_delete_check = QCheckBox(t("confirm_delete"))
        self.confirm_delete_check.setChecked(True)
        behavior_layout.addWidget(self.confirm_delete_check)

        self.hide_completed_groups_check = QCheckBox(t("hide_completed_groups"))
        behavior_layout.addWidget(self.hide_completed_groups_check)
        
        layout.addWidget(behavior_group)
        layout.addStretch()

        return self._wrap_tab(content)

    def _build_maintenance_tab(self) -> QWidget:
        """Build system tab (general + maintenance)."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        general_group = QGroupBox(t("settings_general_group"))
        general_layout = QVBoxLayout(general_group)

        lang_row = QHBoxLayout()
        lang_row.addWidget(self._make_field_label(t("settings_language_label")))
        self.language_combo = QComboBox()
        self._install_no_wheel(self.language_combo)
        for code, name in get_available_languages().items():
            self.language_combo.addItem(name, code)
        lang_row.addWidget(self.language_combo, stretch=1)
        general_layout.addLayout(lang_row)

        theme_row = QHBoxLayout()
        theme_row.addWidget(self._make_field_label(t("settings_theme_label")))
        self.theme_combo = QComboBox()
        self._install_no_wheel(self.theme_combo)
        self.theme_combo.addItem(t("theme_dark"), "dark")
        self.theme_combo.addItem(t("theme_light"), "light")
        theme_row.addWidget(self.theme_combo, stretch=1)
        general_layout.addLayout(theme_row)

        layout.addWidget(general_group)

        maintenance_group = QGroupBox(t("maintenance"))
        maintenance_layout = QVBoxLayout(maintenance_group)

        self.clear_cache_btn = QPushButton(t("clear_cache"))
        self._connect_signal(self.clear_cache_btn.clicked, self._clear_cache)
        maintenance_layout.addWidget(self.clear_cache_btn)

        self.reset_pipeline_btn = QPushButton(t("reset_pipeline_db"))
        self._connect_signal(self.reset_pipeline_btn.clicked, self._reset_pipeline_state)
        maintenance_layout.addWidget(self.reset_pipeline_btn)

        self.check_updates_btn = QPushButton(t("check_for_updates"))
        self._connect_signal(self.check_updates_btn.clicked, self._check_updates_now)
        maintenance_layout.addWidget(self.check_updates_btn)

        layout.addWidget(maintenance_group)

        legal_group = QGroupBox(t("settings_legal_group"))
        legal_layout = QVBoxLayout(legal_group)

        self.open_impressum_btn = QPushButton(t("open_impressum"))
        self._connect_signal(self.open_impressum_btn.clicked, lambda: self._open_legal_document("impressum.html"))
        legal_layout.addWidget(self.open_impressum_btn)

        self.open_privacy_btn = QPushButton(t("open_privacy_policy"))
        self._connect_signal(self.open_privacy_btn.clicked, lambda: self._open_legal_document("datenschutz.html"))
        legal_layout.addWidget(self.open_privacy_btn)

        self.open_agb_btn = QPushButton(t("open_terms_conditions"))
        self._connect_signal(self.open_agb_btn.clicked, lambda: self._open_legal_document("agb.html"))
        legal_layout.addWidget(self.open_agb_btn)

        layout.addWidget(legal_group)
        layout.addStretch()
        return self._wrap_tab(content)

    def _resolve_legal_document_path(self, filename: str) -> Path | None:
        """Resolve legal document path across dev and frozen layouts."""
        app_dir = AppConfig.get_app_dir()
        candidates = [
            app_dir / "website" / filename,
            app_dir / "src" / "photo_cleaner" / "legal" / filename,
            app_dir / "photo_cleaner" / "legal" / filename,
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _open_legal_document(self, filename: str) -> None:
        """Open a legal HTML document in an in-app dialog."""
        document_path = self._resolve_legal_document_path(filename)
        if not document_path:
            QMessageBox.warning(
                self,
                t("legal_docs_missing_title"),
                t("legal_docs_missing_msg").format(name=filename),
            )
            return

        try:
            html_content = document_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            QMessageBox.warning(
                self,
                t("legal_docs_missing_title"),
                t("legal_docs_open_failed").format(name=f"{filename}\n{e}"),
            )
            return

        title_map = {
            "impressum.html": t("open_impressum"),
            "datenschutz.html": t("open_privacy_policy"),
            "agb.html": t("open_terms_conditions"),
        }
        dialog_title = title_map.get(filename, filename)
        base_url = QUrl.fromLocalFile(str(document_path.parent) + "/")
        dialog = LegalDocumentDialog(dialog_title, html_content, base_url, self)
        dialog.exec()

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

    def _make_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label

    def _make_field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setMinimumWidth(130)
        return label

    def _install_no_wheel(self, widget) -> None:
        widget.setFocusPolicy(Qt.StrongFocus)
        widget.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Wheel and isinstance(obj, (QSlider, QSpinBox, QComboBox)):
            if not obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)
    
    def _load_settings(self):
        """Load current settings from config."""
        if self.config_system:
            try:
                # Quality settings
                self.blur_slider.setValue(
                    int(self.config_system.get_config('blur_weight', 0.5) * 100)
                )
                self.contrast_slider.setValue(
                    int(self.config_system.get_config('contrast_weight', 0.3) * 100)
                )
                self.exposure_slider.setValue(
                    int(self.config_system.get_config('exposure_weight', 0.15) * 100)
                )
                self.noise_slider.setValue(
                    int(self.config_system.get_config('noise_weight', 0.05) * 100)
                )

                # Detection settings
                self.closed_eyes_check.setChecked(
                    self.config_system.get_config('detect_closed_eyes', True)
                )
                self.redeye_check.setChecked(
                    self.config_system.get_config('detect_redeye', True)
                )
                self.blurry_check.setChecked(
                    self.config_system.get_config('detect_blurry', True)
                )
                self.underexposed_check.setChecked(
                    self.config_system.get_config('detect_underexposed', True)
                )
                self.overexposed_check.setChecked(
                    self.config_system.get_config('detect_overexposed', False)
                )
                self.hide_completed_groups_check.setChecked(
                    self.config_system.get_config('hide_completed_groups', False)
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Could not load config-system settings: {e}")

        settings = AppConfig.get_user_settings()
        dialog_settings = settings.get("settings_dialog", {})

        current_format = AppConfig.get_export_format()
        format_idx = self.export_format_combo.findData(current_format)
        self.export_format_combo.setCurrentIndex(max(0, format_idx))
        self.export_quality_spin.setValue(AppConfig.get_export_quality())
        current_structure = AppConfig.get_export_structure()
        idx = self.export_structure_combo.findData(current_structure)
        self.export_structure_combo.setCurrentIndex(max(0, idx))
        t1, k1, t2, k2, k3 = AppConfig.get_auto_keep_tiers()
        self.tier1_threshold_spin.setValue(t1)
        self.tier1_keep_spin.setValue(k1)
        self.tier2_threshold_spin.setValue(t2)
        self.tier2_keep_spin.setValue(k2)
        self.tier3_keep_spin.setValue(k3)
        self.keep_originals_check.setChecked(bool(dialog_settings.get("keep_originals", True)))
        self.auto_backup_check.setChecked(bool(dialog_settings.get("auto_backup", True)))
        self.confirm_delete_check.setChecked(bool(dialog_settings.get("confirm_delete", True)))

        self.similarity_spin.setValue(int(dialog_settings.get("similarity_threshold", 85)))
        self.group_time_window_spin.setValue(int(dialog_settings.get("group_time_window_sec", 30)))
        self.group_relaxed_similarity_spin.setValue(int(dialog_settings.get("group_relaxed_similarity", 60)))
        advanced_enabled = bool(dialog_settings.get("show_advanced", False))
        self.show_advanced_check.setChecked(advanced_enabled)
        self.advanced_group.setVisible(advanced_enabled)

        current_lang = get_language()
        lang_index = self.language_combo.findData(current_lang)
        if lang_index >= 0:
            self.language_combo.setCurrentIndex(lang_index)

        current_theme = get_theme()
        theme_index = self.theme_combo.findData(current_theme)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)
    
    def _on_preset_selected(self, preset_name: str):
        """Handle preset selection."""
        if not self.preset_manager:
            return
        
        try:
            preset = self.preset_manager.get_preset(preset_name)
            if preset:
                # Load preset values into sliders
                if hasattr(preset, 'to_dict'):
                    data = preset.to_dict()
                elif isinstance(preset, dict):
                    data = preset
                else:
                    return
                
                if 'blur_weight' in data:
                    self.blur_slider.setValue(int(data['blur_weight'] * 100))
                if 'contrast_weight' in data:
                    self.contrast_slider.setValue(int(data['contrast_weight'] * 100))
                if 'exposure_weight' in data:
                    self.exposure_slider.setValue(int(data['exposure_weight'] * 100))
                if 'noise_weight' in data:
                    self.noise_slider.setValue(int(data['noise_weight'] * 100))
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Could not load preset: {e}")
    
    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            t("reset_settings_confirm"),
            t("reset_settings_confirm_msg"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset to defaults
            self.blur_slider.setValue(50)
            self.contrast_slider.setValue(30)
            self.exposure_slider.setValue(15)
            self.noise_slider.setValue(5)
            
            self.closed_eyes_check.setChecked(True)
            self.redeye_check.setChecked(True)
            self.blurry_check.setChecked(True)
            self.underexposed_check.setChecked(True)
            self.overexposed_check.setChecked(False)

            default_format_idx = self.export_format_combo.findData(AppConfig.DEFAULT_EXPORT_FORMAT)
            self.export_format_combo.setCurrentIndex(max(0, default_format_idx))
            self.export_quality_spin.setValue(AppConfig.DEFAULT_EXPORT_QUALITY)
            default_idx = self.export_structure_combo.findData(AppConfig.DEFAULT_EXPORT_STRUCTURE)
            self.export_structure_combo.setCurrentIndex(max(0, default_idx))
            self.tier1_threshold_spin.setValue(AppConfig.DEFAULT_TIER1_THRESHOLD)
            self.tier1_keep_spin.setValue(AppConfig.DEFAULT_TIER1_KEEP)
            self.tier2_threshold_spin.setValue(AppConfig.DEFAULT_TIER2_THRESHOLD)
            self.tier2_keep_spin.setValue(AppConfig.DEFAULT_TIER2_KEEP)
            self.tier3_keep_spin.setValue(AppConfig.DEFAULT_TIER3_KEEP)
            self.keep_originals_check.setChecked(True)
            self.auto_backup_check.setChecked(True)
            self.confirm_delete_check.setChecked(True)
            self.hide_completed_groups_check.setChecked(False)
            self.similarity_spin.setValue(85)
            self.group_time_window_spin.setValue(30)
            self.group_relaxed_similarity_spin.setValue(60)
            self.show_advanced_check.setChecked(False)
            self.advanced_group.setVisible(False)

    def _check_updates_now(self) -> None:
        """Run a manual update check via parent window callback."""
        parent = self.parent()
        if parent and hasattr(parent, "_check_for_updates"):
            try:
                parent._check_for_updates(show_up_to_date=True)
            except Exception as e:
                logger.warning("Manual update check failed from settings dialog: %s", e, exc_info=True)
                QMessageBox.warning(self, t("update_check_title"), t("update_check_failed").format(error=e))
            return

        QMessageBox.information(
            self,
            t("update_check_title"),
            t("update_check_main_window_only"),
        )

    def _clear_cache(self) -> None:
        """Clear caches for a clean pipeline re-run."""
        if not self.actions:
            QMessageBox.warning(self, t("error"), t("actions_unavailable"))
            return

        reply = QMessageBox.question(
            self,
            t("clear_cache_title"),
            t("clear_cache_confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        result = self.actions.ui_clear_cache()
        if result.get("ok"):
            self._refresh_parent_review_state()
            QMessageBox.information(self, t("cache_cleared_title"), t("cache_cleared_msg"))
        else:
            QMessageBox.warning(self, t("error"), result.get("message", t("cache_clear_failed")))

    def _reset_pipeline_state(self) -> None:
        """Reset pipeline state (groups, decisions, caches)."""
        if not self.actions:
            QMessageBox.warning(self, t("error"), t("actions_unavailable"))
            return

        reply = QMessageBox.question(
            self,
            t("reset_pipeline_title"),
            t("reset_pipeline_confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        result = self.actions.ui_reset_pipeline_state()
        if result.get("ok"):
            self._refresh_parent_review_state()
            QMessageBox.information(self, t("reset_pipeline_done_title"), t("reset_pipeline_done_msg"))
        else:
            QMessageBox.warning(self, t("error"), result.get("message", t("reset_pipeline_failed")))

    def _refresh_parent_review_state(self) -> None:
        """Refresh the main review UI after a maintenance action."""
        parent = self.parent()
        if not parent:
            return

        if hasattr(parent, "_reset_thumbnail_runtime_state"):
            parent._reset_thumbnail_runtime_state()
        if hasattr(parent, "_refresh_mini_thumbnails"):
            parent._refresh_mini_thumbnails()
        if hasattr(parent, "refresh_groups"):
            parent.refresh_groups()
    
    def accept(self):
        """Save settings and close."""
        try:
            if self.config_system:
                # Save quality settings
                self.config_system.request_change(
                    'blur_weight', self.blur_slider.value() / 100, self.change_type.BATCH_UPDATE
                )
                self.config_system.request_change(
                    'contrast_weight', self.contrast_slider.value() / 100, self.change_type.BATCH_UPDATE
                )
                self.config_system.request_change(
                    'exposure_weight', self.exposure_slider.value() / 100, self.change_type.BATCH_UPDATE
                )
                self.config_system.request_change(
                    'noise_weight', self.noise_slider.value() / 100, self.change_type.BATCH_UPDATE
                )

                # Save detection settings
                self.config_system.request_change(
                    'detect_closed_eyes', self.closed_eyes_check.isChecked(), self.change_type.BATCH_UPDATE
                )
                self.config_system.request_change(
                    'detect_redeye', self.redeye_check.isChecked(), self.change_type.BATCH_UPDATE
                )
                self.config_system.request_change(
                    'detect_blurry', self.blurry_check.isChecked(), self.change_type.BATCH_UPDATE
                )
                self.config_system.request_change(
                    'detect_underexposed', self.underexposed_check.isChecked(), self.change_type.BATCH_UPDATE
                )
                self.config_system.request_change(
                    'detect_overexposed', self.overexposed_check.isChecked(), self.change_type.BATCH_UPDATE
                )

                # UI behavior
                self.config_system.request_change(
                    'hide_completed_groups', self.hide_completed_groups_check.isChecked(), self.change_type.BATCH_UPDATE
                )
                self.config_system.apply_immediately()

            # Persist settings that are not part of config_update_system
            settings = AppConfig.get_user_settings()
            settings["settings_dialog"] = {
                "export_format": self.export_format_combo.currentData() or AppConfig.DEFAULT_EXPORT_FORMAT,
                "export_quality": self.export_quality_spin.value(),
                "export_structure": self.export_structure_combo.currentData() or "date",
                "tier1_threshold": self.tier1_threshold_spin.value(),
                "tier1_keep": self.tier1_keep_spin.value(),
                "tier2_threshold": self.tier2_threshold_spin.value(),
                "tier2_keep": self.tier2_keep_spin.value(),
                "tier3_keep": self.tier3_keep_spin.value(),
                "keep_originals": self.keep_originals_check.isChecked(),
                "auto_backup": self.auto_backup_check.isChecked(),
                "confirm_delete": self.confirm_delete_check.isChecked(),
                "similarity_threshold": self.similarity_spin.value(),
                "group_time_window_sec": self.group_time_window_spin.value(),
                "group_relaxed_similarity": self.group_relaxed_similarity_spin.value(),
                "show_advanced": self.show_advanced_check.isChecked(),
            }
            AppConfig.set_user_settings(settings)
            AppConfig.set_export_format(self.export_format_combo.currentData() or AppConfig.DEFAULT_EXPORT_FORMAT)
            AppConfig.set_export_quality(self.export_quality_spin.value())
            AppConfig.set_export_structure(self.export_structure_combo.currentData() or "date")
            AppConfig.set_auto_keep_tiers(
                self.tier1_threshold_spin.value(),
                self.tier1_keep_spin.value(),
                self.tier2_threshold_spin.value(),
                self.tier2_keep_spin.value(),
                self.tier3_keep_spin.value(),
            )

            # Apply grouping env values immediately for current session.
            os.environ["PHOTOCLEANER_GROUP_TIME_WINDOW_SEC"] = str(self.group_time_window_spin.value())
            os.environ["PHOTOCLEANER_GROUP_RELAXED_SIMILARITY"] = str(self.group_relaxed_similarity_spin.value() / 100)

            # Apply language/theme via parent handlers when available.
            parent = self.parent()
            selected_lang = self.language_combo.currentData()
            if parent and selected_lang and hasattr(parent, "_change_language"):
                current_lang = get_language()
                if selected_lang != current_lang:
                    parent._change_language(selected_lang)

            selected_theme = self.theme_combo.currentData()
            if parent and selected_theme and hasattr(parent, "_change_theme"):
                current_theme = get_theme()
                if selected_theme != current_theme:
                    parent._change_theme(selected_theme)

            logger.info("Settings saved successfully")
        except (KeyError, ValueError, TypeError, OSError) as e:
            logger.error(f"Failed to save settings: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                t("no_output_folder_title"),
                f"{t('no_output_folder_msg')}\n{e}"
            )
            return
        
        super().accept()
    
    def closeEvent(self, event):
        """Clean up signal connections on dialog close (QUICK-WIN #4).
        
        Prevents signal accumulation when dialog is opened/closed multiple times.
        Without this, each reopen would add new signal handlers to the old ones.
        """
        # Disconnect all tracked signals
        for signal, slot in self._signal_connections:
            try:
                signal.disconnect(slot)
            except RuntimeError:
                # Signal was already disconnected, ignore
                pass
        
        self._signal_connections.clear()
        super().closeEvent(event)
