"""
Start-Dialog für Input/Output-Ordnerauswahl.
Wird vor dem Hauptfenster angezeigt.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class StartDialog(QDialog):
    """Dialog zur Auswahl von Input- und Output-Ordner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("photo_cleaner_ordnerauswahl"))
        self.setModal(True)
        self.resize(600, 200)

        self.input_path: Optional[Path] = None
        self.output_path: Optional[Path] = None

        self._setup_ui()

    def _setup_ui(self):
        """Erstelle UI-Elemente."""
        layout = QVBoxLayout(self)

        # Titel
        title = QLabel("Willkommen beim Photo Cleaner")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Info-Text
        info = QLabel(
            "Wählen Sie den Input-Ordner mit Ihren Bildern und den Output-Ordner für die sortierten Bilder."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addSpacing(20)

        # Input-Ordner
        input_layout = QHBoxLayout()
        input_label = QLabel(t("inputordner"))
        input_label.setMinimumWidth(100)
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Ordner mit zu sortierenden Bildern...")
        self.input_edit.setReadOnly(True)
        input_btn = QPushButton("Durchsuchen...")
        input_btn.clicked.connect(self._select_input)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(input_btn)
        layout.addLayout(input_layout)

        # Output-Ordner
        output_layout = QHBoxLayout()
        output_label = QLabel(t("outputordner"))
        output_label.setMinimumWidth(100)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Zielordner für sortierte Bilder...")
        self.output_edit.setReadOnly(True)
        output_btn = QPushButton("Durchsuchen...")
        output_btn.clicked.connect(self._select_output)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)

        layout.addSpacing(20)

        # Buttons (Abbrechen / Starten)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        start_btn = QPushButton("Starten")
        start_btn.setDefault(True)
        start_btn.clicked.connect(self._validate_and_start)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(start_btn)
        layout.addLayout(button_layout)

    def _select_input(self):
        """Input-Ordner auswählen."""
        folder = QFileDialog.getExistingDirectory(
            self, "Input-Ordner wählen", str(Path.home())
        )
        if folder:
            self.input_path = Path(folder)
            self.input_edit.setText(str(self.input_path))

    def _select_output(self):
        """Output-Ordner auswählen."""
        folder = QFileDialog.getExistingDirectory(
            self, "Output-Ordner wählen", str(Path.home())
        )
        if folder:
            self.output_path = Path(folder)
            self.output_edit.setText(str(self.output_path))

    def _validate_and_start(self):
        """Validiere Auswahl und starte Prozess."""
        # Validierung Input
        if not self.input_path or not self.input_path.exists():
            QMessageBox.warning(
                self,
                "Fehlende Auswahl",
                "Bitte wählen Sie einen gültigen Input-Ordner.",
            )
            return

        # Validierung Output
        if not self.output_path:
            QMessageBox.warning(
                self,
                "Fehlende Auswahl",
                "Bitte wählen Sie einen gültigen Output-Ordner.",
            )
            return

        # Warnung wenn Input und Output identisch
        if self.input_path.resolve() == self.output_path.resolve():
            QMessageBox.warning(
                self,
                "Ungültige Auswahl",
                "Input- und Output-Ordner dürfen nicht identisch sein.",
            )
            return

        # Warnung wenn Output in Input liegt (oder umgekehrt)
        try:
            if self.output_path.resolve() in self.input_path.resolve().parents:
                QMessageBox.warning(
                    self,
                    "Ungültige Auswahl",
                    "Output-Ordner darf nicht innerhalb des Input-Ordners liegen.",
                )
                return
            if self.input_path.resolve() in self.output_path.resolve().parents:
                QMessageBox.warning(
                    self,
                    "Ungültige Auswahl",
                    "Input-Ordner darf nicht innerhalb des Output-Ordners liegen.",
                )
                return
        except (ValueError, TypeError):
            logger.debug("Path comparison error", exc_info=True)
            # Ignoriere Fehler bei Pfadvergleich

        # Output-Ordner erstellen falls nötig
        try:
            self.output_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Output-Ordner konnte nicht erstellt werden:\n{e}",
            )
            return

        # Alles OK → Dialog schließen
        self.accept()

    def get_paths(self) -> Tuple[Path, Path]:
        """Gibt Input- und Output-Pfad zurück."""
        return self.input_path, self.output_path
