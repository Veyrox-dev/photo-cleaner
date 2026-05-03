"""
Installation Dialog for PhotoCleaner Dependencies
==================================================

Benutzerfreundlicher Ein-Klick-Installationsassistent für:
- MediaPipe (Stage 3)
- dlib (Stage 2)
- Automatische System-Empfehlungen
- Fortschrittsanzeige während Installation
- User-Space Installation (keine Admin-Rechte)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QProgressBar, QTextEdit, QGroupBox, QRadioButton,
    QButtonGroup, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
import logging

from photo_cleaner.dependency_manager import DependencyManager
from photo_cleaner.i18n import t

logger = logging.getLogger(__name__)


class InstallationWorker(QThread):
    """Worker-Thread für Package-Installation (nicht-blockierend)"""
    
    progress_updated = Signal(float, str)  # (progress, message)
    installation_complete = Signal(bool, str)  # (success, message)
    
    def __init__(self, manager: DependencyManager, packages: list):
        super().__init__()
        self.manager = manager
        self.packages = packages  # Liste von package_keys
    
    def run(self):
        """Führe Installation aus"""
        total_packages = len(self.packages)
        
        for i, package_key in enumerate(self.packages):
            # Update Gesamt-Fortschritt
            base_progress = i / total_packages
            
            def progress_callback(package_progress: float, message: str):
                # Kombiniere Gesamt- und Package-Fortschritt
                total_progress = base_progress + (package_progress / total_packages)
                self.progress_updated.emit(total_progress, message)
            
            # Installiere Package
            success, message = self.manager.install_package(package_key, progress_callback)
            
            if not success:
                self.installation_complete.emit(
                    False,
                    t("installation_error_package").format(package=package_key, message=message),
                )
                return
        
        # Alle erfolgreich
        self.installation_complete.emit(True, t("installation_all_packages_installed"))


class InstallationDialog(QDialog):
    """
    Haupt-Installations-Dialog für erweiterte Funktionen
    
    Features:
    - System-Analyse und Empfehlungen
    - Checkbox-Auswahl für MediaPipe/dlib
    - Radio-Button für "Beide installieren"
    - Fortschrittsbalken
    - Log-Anzeige
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = DependencyManager()
        self.installation_worker = None
        
        self.setWindowTitle(t("installation_title"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self._setup_ui()
        self._load_current_status()
    
    def _setup_ui(self):
        """Erstelle UI-Layout"""
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(t("installation_title"))
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # System-Info Gruppe
        system_group = self._create_system_info_group()
        layout.addWidget(system_group)
        
        # Package-Auswahl Gruppe
        package_group = self._create_package_selection_group()
        layout.addWidget(package_group)
        
        # Empfehlung
        self.recommendation_label = QLabel()
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setStyleSheet("QLabel { background-color: #e8f4f8; padding: 10px; border-radius: 5px; }")
        layout.addWidget(self.recommendation_label)
        
        # Fortschrittsbalken
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log-Anzeige
        log_label = QLabel(t("installation_log"))
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("QTextEdit { background-color: #f5f5f5; font-family: monospace; }")
        layout.addWidget(self.log_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.install_button = QPushButton(t("install_button"))
        self.install_button.clicked.connect(self._start_installation)
        self.install_button.setMinimumHeight(35)
        button_layout.addWidget(self.install_button)
        
        self.cancel_button = QPushButton(t("close_button"))
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_system_info_group(self) -> QGroupBox:
        """Erstelle System-Info Gruppe"""
        group = QGroupBox(t("installation_system_info_title"))
        layout = QVBoxLayout()
        
        info = self.manager.system_info
        
        # OS & Python
        os_label = QLabel(t("installation_os_label").format(name=info.os_name, version=info.os_version))
        layout.addWidget(os_label)
        
        arch = t("installation_arch_64") if info.is_64bit else t("installation_arch_32")
        python_label = QLabel(t("installation_python_label").format(version=info.python_version, arch=arch))
        layout.addWidget(python_label)
        
        # CPU & GPU
        cpu_label = QLabel(t("installation_cpu_cores_label").format(count=info.cpu_cores))
        layout.addWidget(cpu_label)
        
        gpu_state = t("installation_state_available") if info.has_gpu else t("installation_state_not_detected")
        gpu_label = QLabel(t("installation_gpu_label").format(state=gpu_state))
        layout.addWidget(gpu_label)
        
        # Build Tools (wichtig für dlib)
        bt_state = t("installation_state_available") if info.has_build_tools else t("installation_state_not_detected")
        bt_label = QLabel(t("installation_build_tools_label").format(state=bt_state))
        if not info.has_build_tools:
            bt_label.setToolTip(t("build_tools_required"))
        layout.addWidget(bt_label)
        
        group.setLayout(layout)
        return group
    
    def _create_package_selection_group(self) -> QGroupBox:
        """Erstelle Package-Auswahl Gruppe"""
        group = QGroupBox(t("installation_packages_title"))
        layout = QVBoxLayout()
        
        # Radio Button Group für Auswahl
        self.selection_group = QButtonGroup()
        
        # MediaPipe Option
        mediapipe_dep = self.manager.dependencies["mediapipe"]
        self.mediapipe_radio = QRadioButton()
        mediapipe_layout = QHBoxLayout()
        
        mediapipe_label = QLabel(
            t("installation_mediapipe_description").format(size=mediapipe_dep.size_mb)
        )
        mediapipe_label.setWordWrap(True)
        
        mediapipe_layout.addWidget(self.mediapipe_radio)
        mediapipe_layout.addWidget(mediapipe_label, 1)
        
        if mediapipe_dep.installed:
            mediapipe_status = QLabel(t("installation_installed"))
            mediapipe_status.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            mediapipe_layout.addWidget(mediapipe_status)
            self.mediapipe_radio.setEnabled(False)
        
        layout.addLayout(mediapipe_layout)
        self.selection_group.addButton(self.mediapipe_radio, 1)
        
        # dlib Option
        dlib_dep = self.manager.dependencies["dlib"]
        self.dlib_radio = QRadioButton()
        dlib_layout = QHBoxLayout()
        
        dlib_label = QLabel(
            t("installation_dlib_description").format(size=dlib_dep.size_mb)
        )
        dlib_label.setWordWrap(True)
        
        dlib_layout.addWidget(self.dlib_radio)
        dlib_layout.addWidget(dlib_label, 1)
        
        if dlib_dep.installed:
            dlib_status = QLabel(t("installation_installed"))
            dlib_status.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            dlib_layout.addWidget(dlib_status)
            self.dlib_radio.setEnabled(False)
        elif not self.manager.system_info.has_build_tools:
            warning_label = QLabel(t("installation_build_tools_missing"))
            warning_label.setStyleSheet("QLabel { color: orange; font-weight: bold; }")
            warning_label.setToolTip(t("installation_build_tools_missing_tooltip"))
            dlib_layout.addWidget(warning_label)
        
        layout.addLayout(dlib_layout)
        self.selection_group.addButton(self.dlib_radio, 2)
        
        # Beide installieren Option
        self.both_radio = QRadioButton()
        both_layout = QHBoxLayout()
        
        both_label = QLabel(t("install_both_option"))
        both_label.setWordWrap(True)
        
        both_layout.addWidget(self.both_radio)
        both_layout.addWidget(both_label, 1)
        
        layout.addLayout(both_layout)
        self.selection_group.addButton(self.both_radio, 3)
        
        # Standard-Auswahl basierend auf Empfehlung
        if self.manager.recommendation.recommended_package == "mediapipe":
            self.mediapipe_radio.setChecked(True)
        elif self.manager.recommendation.recommended_package == "dlib":
            self.dlib_radio.setChecked(True)
        else:
            # Beide schon installiert oder keine klare Empfehlung
            if not mediapipe_dep.installed and not dlib_dep.installed:
                self.both_radio.setChecked(True)
        
        group.setLayout(layout)
        return group
    
    def _load_current_status(self):
        """Lade aktuellen Status und zeige Empfehlung"""
        rec = self.manager.recommendation
        
        if rec.recommended_package == "none":
            self.recommendation_label.setText(
                t("installation_already_installed")
            )
            self.recommendation_label.setStyleSheet(
                "QLabel { background-color: #d4edda; padding: 10px; border-radius: 5px; color: #155724; }"
            )
            self.install_button.setEnabled(False)
            self.install_button.setText(t("complete"))
        else:
            # Zeige Empfehlung
            rec_text = t("installation_recommendation_prefix").format(package=rec.recommended_package)
            rec_text += f"<i>{rec.reason}</i>"
            
            if rec.warning:
                rec_text += f"<br><br>{rec.warning}"
            
            self.recommendation_label.setText(rec_text)
        
        # Log initial status
        self._log_message(self.manager.generate_report())
    
    def _start_installation(self):
        """Starte Installation-Prozess"""
        # Bestimme zu installierende Pakete
        packages = []
        
        if self.mediapipe_radio.isChecked():
            packages.append("mediapipe")
        elif self.dlib_radio.isChecked():
            packages.append("dlib")
        elif self.both_radio.isChecked():
            if not self.manager.dependencies["mediapipe"].installed:
                packages.append("mediapipe")
            if not self.manager.dependencies["dlib"].installed:
                packages.append("dlib")
        
        if not packages:
            QMessageBox.information(self, t("information"), t("installation_select_package"))
            return
        
        # Bestätigungsdialog
        package_names = [self.manager.dependencies[p].name for p in packages]
        confirm = QMessageBox.question(
            self,
            t("license_confirm_activation"),
            t("installation_confirm_packages").format(packages=", ".join(package_names)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
        
        # UI für Installation vorbereiten
        self.install_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self._log_message(
            "\n"
            + "=" * 60
            + "\n"
            + t("installation_start_log").format(packages=", ".join(package_names))
            + "\n"
            + "=" * 60
            + "\n"
        )
        
        # Starte Worker-Thread
        self.installation_worker = InstallationWorker(self.manager, packages)
        self.installation_worker.progress_updated.connect(self._on_progress_update)
        self.installation_worker.installation_complete.connect(self._on_installation_complete)
        self.installation_worker.start()
    
    def _on_progress_update(self, progress: float, message: str):
        """Handle Progress-Update vom Worker"""
        self.progress_bar.setValue(int(progress * 100))
        self._log_message(message)
    
    def _on_installation_complete(self, success: bool, message: str):
        """Handle Installation-Abschluss"""
        self._log_message(f"\n{message}\n")
        
        self.progress_bar.setVisible(False)
        self.install_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        
        if success:
            QMessageBox.information(
                self,
                t("finalize_success"),
                t("installation_success_message").format(message=message)
            )
            
            # Aktualisiere Manager
            self.manager = DependencyManager()
            
            # Schließe Dialog
            self.accept()
        else:
            QMessageBox.critical(
                self,
                t("finalize_failed"),
                t("installation_failure_message").format(message=message)
            )
    
    def _log_message(self, message: str):
        """Füge Nachricht zum Log hinzu"""
        self.log_text.append(message)
        # Auto-scroll zum Ende
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )


if __name__ == "__main__":
    """Test-Modus"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    dialog = InstallationDialog()
    dialog.exec()
    
    sys.exit()
