"""Splash Screen für PhotoCleaner mit Ladefortschritt.

Zeigt sofort beim Start einen Splash Screen an, um dem Nutzer
Feedback zu geben während schwere Module geladen werden.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from photo_cleaner.i18n import t


class PhotoCleanerSplashScreen(QSplashScreen):
    """Splash Screen mit Ladefortschritt für PhotoCleaner."""
    
    def __init__(self, app_dir: Path | None = None):
        """Initialisiere Splash Screen.
        
        Args:
            app_dir: App-Verzeichnis für Icon-Suche (optional)
        """
        pixmap = self._create_splash_pixmap()
        super().__init__(pixmap)
        
        # Window flags: vermeiden Always-on-Top, um Taskleiste/Window-Fokus nicht zu stören
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SplashScreen
        )

        # Ensure splash is fully destroyed when closed
        from PySide6.QtCore import Qt as _Qt
        try:
            self.setAttribute(_Qt.WidgetAttribute.WA_DeleteOnClose, True)
        except (RuntimeError, AttributeError, TypeError):
            pass
        
        # Zentriere auf Bildschirm
        self.center_on_screen()
        
        # Zeige sofort
        self.show()
        QApplication.processEvents()
    
    def center_on_screen(self):
        """Zentriere Splash Screen auf dem Bildschirm."""
        screen = QApplication.primaryScreen().geometry()
        splash_geometry = self.geometry()
        x = (screen.width() - splash_geometry.width()) // 2
        y = (screen.height() - splash_geometry.height()) // 2
        self.move(x, y)
    
    def _create_splash_pixmap(self) -> QPixmap:
        """Erstelle ein einfaches Splash-Bild programmatisch.
        
        Returns:
            QPixmap mit Splash-Design
        """
        width, height = 500, 300
        pixmap = QPixmap(width, height)
        
        # Hintergrund: Dunkler Gradient
        pixmap.fill(QColor(45, 45, 45))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Titel
        title_font = QFont("Segoe UI", 28, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            0, 80, width, 50, 
            Qt.AlignmentFlag.AlignCenter, 
            "PhotoCleaner"
        )
        
        # Version
        version_font = QFont("Segoe UI", 12)
        painter.setFont(version_font)
        painter.setPen(QColor(180, 180, 180))
        painter.drawText(
            0, 130, width, 30, 
            Qt.AlignmentFlag.AlignCenter, 
            f"{t('splash_version')} 0.8.6"
        )
        
        # Accent-Linie
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(42, 130, 218))  # Blauer Akzent
        painter.drawRect(150, 170, 200, 4)
        
        painter.end()
        return pixmap
    
    def show_progress(self, message: str, progress: int = 0):
        """Zeige Ladefortschritt an.
        
        Args:
            message: Statusmeldung (z.B. "Lade OpenCV...")
            progress: Fortschritt in Prozent (0-100)
        """
        # Formatiere Nachricht mit Fortschritt
        if progress > 0:
            full_message = f"{message}... {progress}%"
        else:
            full_message = f"{message}..."
        
        self.showMessage(
            full_message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            QColor(255, 255, 255)
        )
        QApplication.processEvents()
    
    def finish_with_window(self, window):
        """Beende Splash Screen zuverlässig und zeige Hauptfenster.

        Entfernt "always on top", ruft finish(), und erzwingt anschließendes
        Verstecken und Freigeben, um Hänger zu vermeiden.

        Args:
            window: Hauptfenster das angezeigt werden soll
        """
        def _do_finish():
            try:
                # Remove always-on-top to avoid lingering above main window
                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint |
                    Qt.WindowType.SplashScreen
                )
            except (RuntimeError, AttributeError):
                pass
            try:
                self.finish(window)
            except (RuntimeError, TypeError):
                # Fallback: just hide if finish fails
                try:
                    self.hide()
                except (RuntimeError, AttributeError):
                    pass
            # Force close to ensure splash disappears
            try:
                self.hide()
                self.close()
                self.deleteLater()
                QApplication.processEvents()
            except (RuntimeError, AttributeError):
                pass

        # Short delay for smoother transition, then robust finish
        QTimer.singleShot(500, _do_finish)


def create_splash_screen(app_dir: Path | None = None) -> PhotoCleanerSplashScreen:
    """Factory-Funktion für einfache Erstellung.
    
    Args:
        app_dir: App-Verzeichnis für Icon-Suche (optional)
    
    Returns:
        Initialisierter Splash Screen
    """
    return PhotoCleanerSplashScreen(app_dir)
