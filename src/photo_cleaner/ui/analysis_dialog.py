"""
Dialog für Analyse-Phase mit Fortschrittsanzeige.
Führt Pipeline im Hintergrund aus und zeigt Fortschritt an.
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
)

from photo_cleaner.pipeline.pipeline import PhotoCleanerPipeline
from photo_cleaner.i18n import t

logger = logging.getLogger(__name__)


class PipelineWorker(QThread):
    """Worker-Thread für Pipeline-Ausführung."""

    progress = Signal(int, str)  # (percent, status_text)
    finished = Signal(bool, str)  # (success, message)

    def __init__(self, input_path: Path, db_path: Path):
        super().__init__()
        self.input_path = input_path
        self.db_path = db_path
        self.pipeline: Optional[PhotoCleanerPipeline] = None
        self._should_cancel = False

    def run(self):
        """Führt Pipeline aus."""
        try:
            from photo_cleaner.db.schema import Database
            from pathlib import Path
            
            self.progress.emit(0, t("initializing"))

            # WICHTIG: Lösche alte Datenbank falls sie existiert
            # Das erzwingt einen frischen Index und verhindert Pfad-Konflikte
            if self.db_path.exists():
                try:
                    self.db_path.unlink()
                    logger.info(f"Alte Datenbank gelöscht: {self.db_path}")
                except Exception as e:
                    logger.warning(f"Konnte alte Datenbank nicht löschen: {e}")

            # Database erstellen und verbinden
            db = Database(self.db_path)
            db.conn = db.connect()  # Connection explizit öffnen

            # Pipeline erstellen
            self.pipeline = PhotoCleanerPipeline(
                db=db,
                config=None,  # Verwendet Default-Config
            )

            # Pipeline ausführen
            if self._should_cancel:
                self.finished.emit(False, t("cancel"))
                return
            
            self.progress.emit(10, t("analyzing"))
            
            # Führe Pipeline aus (ruft alle Stages auf)
            stats = self.pipeline.run(self.input_path)
            
            # Fortschritt simulieren (run() führt alles intern aus)
            self.progress.emit(100, t("analysis_completed"))
            
            # Erfolgsmeldung mit Statistiken
            message = (
                f"Analyse erfolgreich abgeschlossen!\n\n"
                f"Indexiert: {stats.indexed_files} Bilder\n"
                f"Duplikate: {stats.duplicate_groups} Gruppen mit {stats.total_duplicates} Bildern\n"
                f"Auto-Auswahl: {stats.duplicate_groups} beste Bilder markiert"
            )
            self.finished.emit(True, message)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.finished.emit(False, f"{t('error')}: {e}")

    def cancel(self):
        """Bricht Pipeline ab."""
        self._should_cancel = True


class AnalysisDialog(QDialog):
    """Dialog für Analyse-Phase mit Fortschrittsanzeige."""

    def __init__(self, input_path: Path, db_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("analyzing"))
        self.setModal(True)
        self.setMinimumWidth(500)

        self.input_path = input_path
        self.db_path = db_path
        self.worker: Optional[PipelineWorker] = None
        self.analysis_success = False

        self._setup_ui()
        self._start_analysis()

    def _setup_ui(self):
        """Erstelle UI-Elemente."""
        layout = QVBoxLayout(self)

        # Titel
        self.title_label = QLabel(t("analysis_running"))
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Status
        self.status_label = QLabel(t("initializing"))
        layout.addWidget(self.status_label)

        # Fortschrittsbalken
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Info-Text
        info = QLabel(t("analysis_wait"))
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)

        layout.addSpacing(20)

        # Abbrechen-Button (nur während Analyse)
        self.cancel_btn = QPushButton(t("cancel_analysis"))
        self.cancel_btn.clicked.connect(self._cancel_analysis)
        layout.addWidget(self.cancel_btn)

        # Schließen-Button (nach Analyse)
        self.close_btn = QPushButton(t("close"))
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)
        layout.addWidget(self.close_btn)

    def _start_analysis(self):
        """Startet Pipeline im Hintergrund."""
        self.worker = PipelineWorker(self.input_path, self.db_path)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._analysis_finished)
        self.worker.start()

    def _update_progress(self, percent: int, status_text: str):
        """Aktualisiert Fortschrittsanzeige."""
        self.progress_bar.setValue(percent)
        self.status_label.setText(status_text)

    def _analysis_finished(self, success: bool, message: str):
        """Wird aufgerufen wenn Analyse fertig ist."""
        self.analysis_success = success

        if success:
            self.title_label.setText(t("analysis_completed"))
            self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
            self.status_label.setText(message)
        else:
            self.title_label.setText(t("analysis_failed"))
            self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")
            self.status_label.setText(message)

        # UI anpassen
        self.cancel_btn.setVisible(False)
        self.close_btn.setVisible(True)
        self.close_btn.setDefault(True)

        # Automatisch schließen bei Erfolg
        if success:
            self.accept()

    def _cancel_analysis(self):
        """Bricht Analyse ab."""
        if self.worker and self.worker.isRunning():
            self.status_label.setText(t("cancel"))
            self.cancel_btn.setEnabled(False)
            self.worker.cancel()
            return
        self.reject()

    def closeEvent(self, event):
        """Verhindert Schließen während Analyse läuft."""
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
