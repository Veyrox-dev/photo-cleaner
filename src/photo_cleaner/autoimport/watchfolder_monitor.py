"""
WatchfolderMonitor: Qt-basierter Watchfolder-Monitor mit QFileSystemWatcher.

Verantwortung:
    - Registriert/deregistriert Watchfolders
    - Emitiert Signale bei Dateiänderungen
    - Puffert Events für Debounce-Handler
"""

import logging
from pathlib import Path
from PySide6.QtCore import QObject, QFileSystemWatcher, pyqtSignal

logger = logging.getLogger(__name__)


class WatchfolderMonitor(QObject):
    """Qt-basierter Watchfolder-Monitor mit Multi-Path-Support."""
    
    # Signale
    file_added = pyqtSignal(str)  # path: str
    file_modified = pyqtSignal(str)  # path: str
    file_removed = pyqtSignal(str)  # path: str
    error_occurred = pyqtSignal(str)  # error_message: str
    
    # Unterstützte Bildformate
    SUPPORTED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
        '.raw', '.cr2', '.nef', '.arw', '.raf', '.dng', '.webp'
    }
    
    def __init__(self):
        """Initialisiert den Monitor."""
        super().__init__()
        self._watcher = QFileSystemWatcher()
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_directory_changed)
        self._watched_paths = {}  # {path_str: label}
        logger.debug("WatchfolderMonitor initialisiert")
    
    def add_watchfolder(self, folder_path: Path, label: str = None) -> bool:
        """
        Registriert einen Watchfolder.
        
        Args:
            folder_path: Path zum zu überwachenden Ordner
            label: Optionales Label für UI-Anzeige
        
        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        if not isinstance(folder_path, Path):
            folder_path = Path(folder_path)
        
        if not folder_path.is_dir():
            error_msg = f"Path ist kein Verzeichnis: {folder_path}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        
        folder_str = str(folder_path)
        if folder_str in self._watched_paths:
            logger.debug(f"Folder bereits überwacht: {folder_path}")
            return True
        
        try:
            self._watcher.addPath(folder_str)
            self._watched_paths[folder_str] = label or folder_path.name
            logger.info(f"Watchfolder hinzugefügt: {folder_path} (Label: {self._watched_paths[folder_str]})")
            return True
        except Exception as e:
            error_msg = f"Fehler beim Hinzufügen des Watchfolders {folder_path}: {e}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def remove_watchfolder(self, folder_path: Path) -> bool:
        """
        Deregistriert einen Watchfolder.
        
        Args:
            folder_path: Path zum zu entfernenden Ordner
        
        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        if not isinstance(folder_path, Path):
            folder_path = Path(folder_path)
        
        folder_str = str(folder_path)
        
        try:
            self._watcher.removePath(folder_str)
            if folder_str in self._watched_paths:
                del self._watched_paths[folder_str]
            logger.info(f"Watchfolder entfernt: {folder_path}")
            return True
        except Exception as e:
            error_msg = f"Fehler beim Entfernen des Watchfolders {folder_path}: {e}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def get_watched_paths(self) -> dict:
        """
        Gibt alle überwachten Ordner zurück.
        
        Returns:
            Dict: {path_str: label}
        """
        return self._watched_paths.copy()
    
    def is_watching(self, folder_path: Path) -> bool:
        """Prüft, ob ein Ordner überwacht wird."""
        return str(folder_path) in self._watched_paths
    
    def get_label(self, folder_path: Path) -> str:
        """Gibt das Label für einen überwachten Ordner zurück."""
        return self._watched_paths.get(str(folder_path), folder_path.name)
    
    def _on_directory_changed(self, path_str: str):
        """
        Qt-Slot: Verzeichnis hat sich geändert.
        
        Wird aufgerufen, wenn Dateien hinzugefügt/entfernt werden.
        """
        try:
            path_obj = Path(path_str)
            if not path_obj.is_dir():
                return
            
            # Enumerate alle Dateien im Verzeichnis
            for file_path in path_obj.iterdir():
                if file_path.is_file() and self._is_image(file_path):
                    logger.debug(f"WatchfolderMonitor: Neue Datei erkannt: {file_path}")
                    self.file_added.emit(str(file_path))
        
        except Exception as e:
            error_msg = f"Fehler beim Enumurieren von {path_str}: {e}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
    
    def _on_file_changed(self, path_str: str):
        """
        Qt-Slot: Datei wurde geändert.
        
        Für Autoimport: Ignorieren wir Änderungen an existierenden Dateien.
        Wir interessieren uns nur für file_added.
        """
        logger.debug(f"WatchfolderMonitor: Datei geändert: {path_str}")
        # [FILL: optional später für Modify-Events nutzen]
    
    @staticmethod
    def _is_image(path: Path) -> bool:
        """
        Prüft, ob eine Datei ein unterstütztes Bildformat hat.
        
        Args:
            path: Zu prüfende Datei
        
        Returns:
            True wenn Format unterstützt, False sonst
        """
        return path.suffix.lower() in WatchfolderMonitor.SUPPORTED_EXTENSIONS
