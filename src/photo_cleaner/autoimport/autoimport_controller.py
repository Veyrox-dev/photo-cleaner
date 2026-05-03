"""
AutoimportController: Hauptkoordinator für Watchfolders & Autoimport.

Verantwortung:
    - Koordiniert alle Autoimport-Komponenten
    - Lädt/speichert Konfiguration
    - Verwaltet Startup/Shutdown
    - Logging
"""

import json
import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal

from .watchfolder_monitor import WatchfolderMonitor
from .debounced_event_handler import DebouncedEventHandler
from .autoimport_pipeline import AutoimportPipeline

logger = logging.getLogger(__name__)


class AutoimportController(QObject):
    """
    Hauptkoordinator für Watchfolders & Autoimport.
    
    Verbindet alle Komponenten und verwaltet ihren Lifecycle:
        - WatchfolderMonitor: erkennt neue Dateien
        - DebouncedEventHandler: batched Events
        - AutoimportPipeline: führt Analyse durch
    
    Signale an UI für Status-Updates und Ergebnisse.
    """
    
    # Signale für UI
    status_changed = Signal(str)  # status_message: str
    import_complete = Signal(dict)  # result: dict
    
    # Konfigurationsdatei
    CONFIG_FILE = Path.home() / "AppData" / "Roaming" / "PhotoCleaner" / "watchfolders.json"
    
    def __init__(self, db_path: Path, config, license_manager, parent=None):
        """
        Initialisiert den Autoimport-Controller.
        
        Args:
            db_path: Path zur PhotoCleaner SQLite DB
            config: AppConfig-Instanz
            license_manager: Instanz des LicenseManager
            parent: Qt-Parent-Objekt (optional)
        """
        super().__init__(parent)
        self.db_path = db_path
        self.config = config
        self.license_manager = license_manager
        
        # Erstelle Komponenten
        self._monitor = WatchfolderMonitor()
        self._debouncer = DebouncedEventHandler(debounce_ms=3000)
        self._pipeline = AutoimportPipeline(db_path, config, license_manager)
        
        # Verbinde Signale
        self._monitor.file_added.connect(self._debouncer.handle_event)
        self._monitor.error_occurred.connect(self._on_monitor_error)
        
        self._debouncer.analysis_requested.connect(self._on_analysis_requested)
        
        self._pipeline.import_started.connect(self._on_import_started)
        self._pipeline.import_completed.connect(self._on_import_completed)
        self._pipeline.import_error.connect(self._on_import_error)
        
        self._enabled = False
        
        logger.debug("AutoimportController initialisiert")

    def _get_config_value(self, attr_name: str, fallback_method: str, default):
        """Read config values from object attrs or AppConfig classmethods."""
        config_dict = getattr(self.config, "__dict__", {})
        if attr_name in config_dict:
            return getattr(self.config, attr_name)

        getter = None
        if isinstance(self.config, type):
            getter = getattr(self.config, fallback_method, None)
        elif fallback_method in config_dict and callable(config_dict[fallback_method]):
            getter = config_dict[fallback_method]

        if callable(getter):
            try:
                return getter()
            except Exception:
                logger.debug(
                    "AutoimportController: Config getter %s fehlgeschlagen",
                    fallback_method,
                    exc_info=True,
                )

        return default
    
    def startup(self):
        """Initialisiert und startet Autoimport."""
        autoimport_enabled = bool(
            self._get_config_value("autoimport_enabled", "get_autoimport_enabled", False)
        )
        debounce_ms = int(
            self._get_config_value("autoimport_debounce_ms", "get_autoimport_debounce_ms", 3000)
        )

        if not autoimport_enabled:
            logger.info("AutoimportController: Deaktiviert via Konfiguration")
            self._enabled = False
            self.status_changed.emit("Autoimport deaktiviert")
            return

        logger.info("AutoimportController: Starten")
        self._debouncer.set_debounce_window(debounce_ms)
        self._load_watchfolders()
        self._enabled = True
        self.status_changed.emit("Autoimport aktiv")
    
    def shutdown(self):
        """Beendet Autoimport graceful."""
        logger.info("AutoimportController: Herunterfahren")
        
        # Verarbeite offene Events
        self._debouncer.flush()

        # Stoppe laufende Pipeline und deregistriere Watchfolder sauber
        self._pipeline.stop()
        for folder_path in list(self._monitor.get_watched_paths().keys()):
            self._monitor.remove_watchfolder(Path(folder_path))
        
        # Speichere Config
        self._save_watchfolders()
        
        self._enabled = False
        self.status_changed.emit("Autoimport deaktiviert")
    
    def add_watchfolder(self, folder_path: Path, label: str = None) -> bool:
        """
        Fügt einen Watchfolder hinzu.
        
        Args:
            folder_path: Path zum zu überwachenden Ordner
            label: Optionales Label für UI-Anzeige
        
        Returns:
            True wenn erfolgreich
        """
        result = self._monitor.add_watchfolder(folder_path, label)
        if result:
            self._save_watchfolders()
            logger.info(f"Watchfolder hinzugefügt: {folder_path}")
        return result
    
    def remove_watchfolder(self, folder_path: Path) -> bool:
        """
        Entfernt einen Watchfolder.
        
        Args:
            folder_path: Path zum Ordner
        
        Returns:
            True wenn erfolgreich
        """
        result = self._monitor.remove_watchfolder(folder_path)
        if result:
            self._save_watchfolders()
            logger.info(f"Watchfolder entfernt: {folder_path}")
        return result
    
    def get_watchfolders(self) -> list:
        """
        Gibt alle konfigurierten Watchfolders zurück.
        
        Returns:
            Liste von dicts: [{"path": "...", "label": "..."}, ...]
        """
        return [
            {"path": path, "label": label}
            for path, label in self._monitor.get_watched_paths().items()
        ]
    
    def set_debounce_window(self, ms: int):
        """
        Ändert das Debounce-Fenster.
        
        Args:
            ms: Neue Fensterbreite in Millisekunden
        """
        logger.info(f"AutoimportController: Debounce-Fenster geändert auf {ms}ms")
        self._debouncer.set_debounce_window(ms)
    
    def is_enabled(self) -> bool:
        """Gibt an, ob Autoimport aktiv ist."""
        return self._enabled
    
    def is_analyzing(self) -> bool:
        """Gibt an, ob eine Analyse läuft."""
        return self._pipeline.is_running()
    
    def _load_watchfolders(self):
        """Lädt Watchfolders aus Konfigurationsdatei."""
        if not self.CONFIG_FILE.exists():
            logger.debug("AutoimportController: Keine Watchfolders konfiguriert")
            return
        
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            for folder_config in config.get("folders", []):
                if folder_config.get("enabled", True):
                    folder_path = Path(folder_config["path"])
                    label = folder_config.get("label", folder_path.name)
                    
                    if self._monitor.add_watchfolder(folder_path, label):
                        logger.info(f"AutoimportController: Watchfolder geladen: {folder_path} ({label})")
                    else:
                        logger.warning(f"AutoimportController: Konnte Watchfolder nicht laden: {folder_path}")
        
        except Exception as e:
            logger.error(f"AutoimportController: Fehler beim Laden der Konfiguration: {e}", exc_info=True)
    
    def _save_watchfolders(self):
        """Speichert aktuell überwachte Watchfolders in Konfigurationsdatei."""
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        config = {
            "version": "1.0",
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "folders": [
                {
                    "path": path,
                    "label": label,
                    "enabled": True
                }
                for path, label in self._monitor.get_watched_paths().items()
            ]
        }
        
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.debug(f"AutoimportController: Konfiguration gespeichert ({len(config['folders'])} Ordner)")
        except Exception as e:
            logger.error(f"AutoimportController: Fehler beim Speichern der Konfiguration: {e}", exc_info=True)
    
    def _on_analysis_requested(self, file_paths: list):
        """Qt-Slot: Debouncer signalisiert zu analysierende Dateien."""
        if not self._enabled:
            logger.debug("AutoimportController: Analyse angefordert, aber Autoimport nicht aktiv")
            return
        
        logger.info(f"AutoimportController: Analyse angefordert für {len(file_paths)} Dateien")
        self._pipeline.analyze_files(file_paths)
    
    def _on_import_started(self, count: int):
        """Qt-Slot: Pipeline hat Analyse gestartet."""
        logger.info(f"AutoimportController: Analyse gestartet für {count} Bilder")
        self.status_changed.emit(f"Analysiere {count} Bilder...")
    
    def _on_import_completed(self, result: dict):
        """Qt-Slot: Pipeline hat Analyse abgeschlossen."""
        logger.info(f"AutoimportController: Analyse abgeschlossen. "
                   f"{result['total_files']} Dateien, "
                   f"{result['duplicates_found']} Duplikate gefunden")
        
        self.status_changed.emit(f"✓ {result['total_files']} Bilder analysiert")
        self.import_complete.emit(result)
    
    def _on_import_error(self, error_message: str):
        """Qt-Slot: Pipeline hat Fehler gemeldet."""
        logger.error(f"AutoimportController: Fehler in Pipeline: {error_message}")
        self.status_changed.emit(f"✗ Fehler: {error_message}")
    
    def _on_monitor_error(self, error_message: str):
        """Qt-Slot: Monitor hat Fehler gemeldet."""
        logger.error(f"AutoimportController: Fehler im Monitor: {error_message}")
        self.status_changed.emit(f"✗ Monitor-Fehler: {error_message}")
