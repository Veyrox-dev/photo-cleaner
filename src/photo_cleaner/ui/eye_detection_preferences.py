"""
Eye Detection Preferences Dialog for PhotoCleaner (PySide6)

Provides a centralized UI to configure progressive eye detection:
- Mode selection (Stage 1, 2, 3)
- dlib configuration (predictor path, test)
- MediaPipe configuration (static mode, max faces, min detection confidence)
- Advanced thresholds and logging options
- Test section placeholder

Config file: ~/.photocleaner/eye_detection_config.json
Compatible with env vars: PHOTOCLEANER_EYE_DETECTION_STAGE, PHOTOCLEANER_DLIB_PREDICTOR_PATH

Hierarchical config load:
1. eye_detection_config.json (new format, primary)
2. settings.json (legacy AppConfig format)
3. Environment variables (lowest priority)

Auto-migration: On first load of new config, settings from old format are migrated.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QRadioButton,
    QLabel,
    QPushButton,
    QFileDialog,
    QCheckBox,
    QSpinBox,
    QSlider,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QMessageBox,
)

from photo_cleaner.config import AppConfig

logger = logging.getLogger(__name__)
CONFIG_FILENAME = "eye_detection_config.json"
SETTINGS_FILENAME = "settings.json"


@dataclass
class EyeDetectionConfig:
    """Configuration for progressive eye detection system.
    
    Attributes:
        mode: 1=Haar (fast), 2=dlib (balanced), 3=MediaPipe (maximum)
        dlib_predictor_path: Path to shape_predictor_68_face_landmarks.dat
        mediapipe_static_image_mode: Static image mode for Face Mesh
        mediapipe_max_faces: Max number of faces to detect
        mediapipe_min_detection_confidence: Min confidence for face detection
        ear_threshold: Eye Aspect Ratio threshold for open/closed detection
        confidence_threshold: Overall quality confidence threshold
        fallback_enabled: Automatically fall back to lower stage on failure
        log_detailed_metrics: Log detailed detection metrics to logger
    """
    mode: int = 1
    dlib_predictor_path: Optional[str] = None
    mediapipe_static_image_mode: bool = True
    mediapipe_max_faces: int = 5
    mediapipe_min_detection_confidence: float = 0.5
    ear_threshold: float = 0.25
    confidence_threshold: float = 0.7
    fallback_enabled: bool = True
    log_detailed_metrics: bool = False

    @staticmethod
    def config_path() -> Path:
        return AppConfig.get_user_data_dir() / CONFIG_FILENAME

    @staticmethod
    def legacy_settings_path() -> Path:
        return AppConfig.get_user_data_dir() / SETTINGS_FILENAME

    @classmethod
    def load(cls) -> "EyeDetectionConfig":
        """Hierarchical config load with migration.
        
        Priority (highest to lowest):
        1. eye_detection_config.json (new format)
        2. settings.json (legacy, migrated on first new-format load)
        3. Environment variables (lowest priority)
        """
        cfg = cls()  # Start with defaults
        
        # === Priority 1: New config file ===
        try:
            new_path = cls.config_path()
            if new_path.exists():
                data = json.load(open(new_path, "r", encoding="utf-8"))
                for k, v in data.items():
                    if hasattr(cfg, k) and k not in ("_migrated",):
                        setattr(cfg, k, v)
                logger.debug(f"Loaded eye detection config from {new_path}")
                return cfg  # If new format exists, use it exclusively
        except Exception as e:
            logger.debug(f"Failed to load new config: {e}")
        
        # === Priority 2: Legacy settings (migrate on first encounter) ===
        try:
            legacy_path = cls.legacy_settings_path()
            if legacy_path.exists():
                legacy_data = json.load(open(legacy_path, "r", encoding="utf-8"))
                # Extract eye detection settings from legacy format
                if "eye_detection_stage" in legacy_data:
                    cfg.mode = int(legacy_data.get("eye_detection_stage", 1))
                if "dlib_predictor_path" in legacy_data:
                    cfg.dlib_predictor_path = legacy_data.get("dlib_predictor_path")
                logger.debug(f"Migrated eye detection settings from legacy {legacy_path}")
                # Save to new format to prevent re-migration
                cfg.save()
        except Exception as e:
            logger.debug(f"Failed to migrate legacy config: {e}")
        
        # === Priority 3: Environment variables (lowest) ===
        try:
            env_stage = os.environ.get("PHOTOCLEANER_EYE_DETECTION_STAGE")
            if env_stage:
                cfg.mode = int(env_stage)
        except (ValueError, TypeError):
            logger.debug("Invalid PHOTOCLEANER_EYE_DETECTION_STAGE value", exc_info=True)
        try:
            env_pred = os.environ.get("PHOTOCLEANER_DLIB_PREDICTOR_PATH")
            if env_pred:
                cfg.dlib_predictor_path = env_pred
        except (ValueError, TypeError):
            logger.debug("Failed to set dlib predictor path from env", exc_info=True)
        
        return cfg

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate config consistency.
        
        Returns:
            (is_valid, error_message)
        """
        if self.mode < 1 or self.mode > 3:
            return False, f"Invalid mode: {self.mode}. Must be 1, 2, or 3."
        
        if self.mode == 2 and not self.dlib_predictor_path:
            return False, "Mode 2 (dlib) requires dlib_predictor_path to be set."
        
        if self.ear_threshold < 0 or self.ear_threshold > 1:
            return False, f"EAR threshold must be in [0, 1], got {self.ear_threshold}"
        
        if self.confidence_threshold < 0 or self.confidence_threshold > 1:
            return False, f"Confidence threshold must be in [0, 1], got {self.confidence_threshold}"
        
        if self.mediapipe_max_faces < 1:
            return False, f"Max faces must be >= 1, got {self.mediapipe_max_faces}"
        
        if self.mediapipe_min_detection_confidence < 0 or self.mediapipe_min_detection_confidence > 1:
            return False, f"MediaPipe detection confidence must be in [0, 1], got {self.mediapipe_min_detection_confidence}"
        
        return True, None

    def save(self) -> None:
        """Persist config to eye_detection_config.json."""
        try:
            path = self.config_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            # Serialize only the fields we care about (skip None for readability)
            data = {k: v for k, v in asdict(self).items() if v is not None}
            json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            logger.debug(f"Saved eye detection config to {path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")


class ConfigManager(QObject):
    """Manages eye detection config with live-apply mechanism.
    
    Emits config_changed signal when config is updated, allowing UI and detectors
    to react and reinitialize.
    """
    config_changed = Signal(dict)  # Emits {"mode": ..., "dlib_predictor_path": ..., ...}
    
    def __init__(self):
        super().__init__()
        self.config = EyeDetectionConfig.load()
    
    def apply_config(self, new_config: EyeDetectionConfig) -> bool:
        """Apply new config with live updates.
        
        Steps:
        1. Validate config
        2. Save to disk
        3. Update environment variables
        4. Emit signal for UI/detector reinit
        
        Returns:
            True if successful, False otherwise.
        """
        is_valid, error_msg = new_config.validate()
        if not is_valid:
            logger.error(f"Config validation failed: {error_msg}")
            return False
        
        try:
            # 1. Save to disk first (so it persists even if env update fails)
            new_config.save()
            
            # 2. Update environment variables (for new analyzer instances)
            os.environ["PHOTOCLEANER_EYE_DETECTION_STAGE"] = str(new_config.mode)
            if new_config.dlib_predictor_path:
                os.environ["PHOTOCLEANER_DLIB_PREDICTOR_PATH"] = new_config.dlib_predictor_path
            else:
                os.environ.pop("PHOTOCLEANER_DLIB_PREDICTOR_PATH", None)
            
            # 3. Update internal state
            self.config = new_config
            
            # 4. Emit signal for UI/analyzer reinit
            config_dict = asdict(new_config)
            config_dict = {k: v for k, v in config_dict.items() if v is not None}
            self.config_changed.emit(config_dict)
            
            logger.info(f"Applied new eye detection config: mode={new_config.mode}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply config: {e}")
            return False


class EyeDetectionPreferencesDialog(QDialog):
    def __init__(self, parent=None, config_manager: Optional[ConfigManager] = None):
        super().__init__(parent)
        self.setWindowTitle(t("augenerkennung_einstellungen"))
        self.resize(700, 600)

        # Load config (use provided manager or create new)
        if config_manager:
            self.config_manager = config_manager
            self.cfg = EyeDetectionConfig.load()  # Reload fresh for dialog
        else:
            self.config_manager = ConfigManager()
            self.cfg = self.config_manager.config

        # Build UI
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Mode selection group
        self.mode_group = QGroupBox("Modus-Auswahl")
        mode_layout = QVBoxLayout(self.mode_group)
        self.rb_stage1 = QRadioButton("Schnell (Stufe 1) - Haar Cascade")
        self.rb_stage2 = QRadioButton("Ausgewogen (Stufe 2) - Haar + dlib (68 Punkte)")
        self.rb_stage3 = QRadioButton("Maximal (Stufe 3) - Haar + dlib + MediaPipe Face Mesh")
        mode_layout.addWidget(self.rb_stage1)
        mode_layout.addWidget(self.rb_stage2)
        mode_layout.addWidget(self.rb_stage3)
        desc = QLabel(t("waehle_die_gewuenschte_genauigkeit_stufe_2_benoeti"))
        desc.setWordWrap(True)
        mode_layout.addWidget(desc)
        root.addWidget(self.mode_group)

        # dlib configuration group
        self.dlib_group = QGroupBox("dlib-Konfiguration (Stufe 2)")
        dlib_form = QFormLayout(self.dlib_group)
        self.dlib_path_edit = QLineEdit()
        self.dlib_path_edit.setPlaceholderText("Pfad zur shape_predictor_68_face_landmarks.dat")
        pick_btn = QPushButton(t("datei_waehlen"))
        pick_btn.clicked.connect(self._choose_dlib_predictor)
        path_row = QHBoxLayout()
        path_row.addWidget(self.dlib_path_edit)
        path_row.addWidget(pick_btn)
        dlib_form.addRow("Predictor-Pfad:", path_row)
        self.dlib_status_label = QLabel(t("status_nicht_geprueft"))
        test_btn = QPushButton("Testen")
        test_btn.clicked.connect(self._test_dlib_setup)
        dlib_form.addRow(test_btn, self.dlib_status_label)
        root.addWidget(self.dlib_group)

        # MediaPipe configuration group
        self.mp_group = QGroupBox("MediaPipe-Konfiguration (Stufe 3)")
        mp_form = QFormLayout(self.mp_group)
        self.mp_static_cb = QCheckBox("Statischer Bildmodus (empfohlen für Fotos)")
        self.mp_static_cb.setChecked(True)
        mp_form.addRow(self.mp_static_cb)
        self.mp_max_faces = QSpinBox()
        self.mp_max_faces.setRange(1, 20)
        self.mp_max_faces.setValue(self.cfg.mediapipe_max_faces)
        mp_form.addRow("Max. Anzahl Gesächer:", self.mp_max_faces)
        self.mp_min_det = QSlider(Qt.Horizontal)
        self.mp_min_det.setRange(0, 100)
        self.mp_min_det.setValue(int(self.cfg.mediapipe_min_detection_confidence * 100))
        mp_form.addRow("Min. Erkennungsgenauigkeit:", self.mp_min_det)
        self.mp_status_label = QLabel(t("status_nicht_geprueft"))
        mp_form.addRow(self.mp_status_label)
        root.addWidget(self.mp_group)

        # Advanced settings group
        self.adv_group = QGroupBox("Erweiterte Einstellungen")
        adv_form = QFormLayout(self.adv_group)
        self.ear_slider = QSlider(Qt.Horizontal)
        self.ear_slider.setRange(0, 50)  # 0.00 - 0.50
        self.ear_slider.setValue(int(self.cfg.ear_threshold * 100))
        adv_form.addRow("Augenmindest-Verhältnis:", self.ear_slider)
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(50, 95)
        self.conf_slider.setValue(int(self.cfg.confidence_threshold * 100))
        adv_form.addRow("Genauigkeits-Schwelle:", self.conf_slider)
        self.fallback_cb = QCheckBox("Auf niedrigere Stufe zurückfallen bei Fehler")
        self.fallback_cb.setChecked(self.cfg.fallback_enabled)
        adv_form.addRow(self.fallback_cb)
        self.log_metrics_cb = QCheckBox("Detaillierte Erkennungsmetriken protokollieren")
        self.log_metrics_cb.setChecked(self.cfg.log_detailed_metrics)
        adv_form.addRow(self.log_metrics_cb)
        root.addWidget(self.adv_group)

        # Test section (placeholder skeleton)
        self.test_group = QGroupBox("Test")
        test_layout = QVBoxLayout(self.test_group)
        row = QHBoxLayout()
        self.test_image_combo = QComboBox()
        self.test_image_combo.addItems(["Beispiel-Porträt", "Beispiel-Gruppe", "Beispiel-Teilweise verdeckt"])  # placeholders
        run_btn = QPushButton(t("test_ausfuehren"))
        run_btn.clicked.connect(self._run_test_placeholder)
        row.addWidget(self.test_image_combo)
        row.addWidget(run_btn)
        test_layout.addLayout(row)
        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["Gesicht ID", "Augen erkannt", "Genauigkeit", "Zeit (ms)"])
        test_layout.addWidget(self.results_table)
        self.test_summary_label = QLabel(t("gesamtgesaecher_erfolgsrate_"))
        test_layout.addWidget(self.test_summary_label)
        root.addWidget(self.test_group)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save_and_close)
        btns.rejected.connect(self.reject)
        # Translate button texts
        for button in btns.buttons():
            if button.text() == "OK":
                button.setText("Speichern")
            elif button.text() == "Cancel":
                button.setText("Abbrechen")
        root.addWidget(btns)

        # Init values from cfg
        self._apply_cfg_to_ui()
        self._update_group_enabled_state()

        # React to mode changes
        self.rb_stage1.toggled.connect(self._update_group_enabled_state)
        self.rb_stage2.toggled.connect(self._update_group_enabled_state)
        self.rb_stage3.toggled.connect(self._update_group_enabled_state)

    # === UI helpers ===
    def _apply_cfg_to_ui(self) -> None:
        # Mode radios
        {1: self.rb_stage1, 2: self.rb_stage2, 3: self.rb_stage3}.get(self.cfg.mode, self.rb_stage1).setChecked(True)
        # dlib path
        self.dlib_path_edit.setText(self.cfg.dlib_predictor_path or "")
        # MediaPipe
        self.mp_static_cb.setChecked(self.cfg.mediapipe_static_image_mode)
        self.mp_max_faces.setValue(self.cfg.mediapipe_max_faces)
        self.mp_min_det.setValue(int(self.cfg.mediapipe_min_detection_confidence * 100))
        # Advanced
        self.ear_slider.setValue(int(self.cfg.ear_threshold * 100))
        self.conf_slider.setValue(int(self.cfg.confidence_threshold * 100))
        self.fallback_cb.setChecked(self.cfg.fallback_enabled)
        self.log_metrics_cb.setChecked(self.cfg.log_detailed_metrics)

    def _update_group_enabled_state(self) -> None:
        stage = self._get_selected_stage()
        self.dlib_group.setEnabled(stage == 2)
        self.mp_group.setEnabled(stage == 3)

    def _get_selected_stage(self) -> int:
        if self.rb_stage2.isChecked():
            return 2
        if self.rb_stage3.isChecked():
            return 3
        return 1

    # === Config persistence ===
    def _save_and_close(self) -> None:
        # Build cfg from UI
        self.cfg.mode = self._get_selected_stage()
        self.cfg.dlib_predictor_path = self.dlib_path_edit.text().strip() or None
        self.cfg.mediapipe_static_image_mode = self.mp_static_cb.isChecked()
        self.cfg.mediapipe_max_faces = int(self.mp_max_faces.value())
        self.cfg.mediapipe_min_detection_confidence = float(self.mp_min_det.value()) / 100.0
        self.cfg.ear_threshold = float(self.ear_slider.value()) / 100.0
        self.cfg.confidence_threshold = float(self.conf_slider.value()) / 100.0
        self.cfg.fallback_enabled = self.fallback_cb.isChecked()
        self.cfg.log_detailed_metrics = self.log_metrics_cb.isChecked()
        
        # Apply config with live updates (saves, env vars, signal)
        if self.config_manager.apply_config(self.cfg):
            self.accept()
        else:
            QMessageBox.critical(self, "Fehler", "Konfiguration konnte nicht angewendet werden. Bitte prüfen Sie die Einstellungen.")

    # === Actions ===
    def _choose_dlib_predictor(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wähle dlib Predictor Datei",
            str(AppConfig.get_user_data_dir()),
            "dlib Predictor (*.dat);;Alle Dateien (*.*)"
        )
        if path:
            self.dlib_path_edit.setText(path)

    def _test_dlib_setup(self) -> None:
        try:
            import dlib  # type: ignore
        except ImportError:
            logger.debug("dlib not installed", exc_info=True)
            self.dlib_status_label.setText("Status: ✗ dlib nicht installiert")
            return
        p = self.dlib_path_edit.text().strip()
        if not p:
            self.dlib_status_label.setText("Status: ✗ Predictor-Pfad nicht gesetzt")
            return
        try:
            _ = dlib.shape_predictor(p)
            self.dlib_status_label.setText("Status: Predictor geladen")
        except (OSError, RuntimeError):
            logger.debug(f"Invalid dlib predictor at {p}", exc_info=True)
            self.dlib_status_label.setText("Status: Predictor ungültig")

    def _run_test_placeholder(self) -> None:
        # Placeholder that clears table and shows a mock result for now
        self.results_table.setRowCount(0)
        self.results_table.insertRow(0)
        self.results_table.setItem(0, 0, QTableWidgetItem("1"))
        self.results_table.setItem(0, 1, QTableWidgetItem("2 Augen"))
        self.results_table.setItem(0, 2, QTableWidgetItem("0.82"))
        self.results_table.setItem(0, 3, QTableWidgetItem("34"))
        self.test_summary_label.setText("Gesamt-Gesächer: 1, Erfolgsrate: 100%")
