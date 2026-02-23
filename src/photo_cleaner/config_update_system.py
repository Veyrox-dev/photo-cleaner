"""
Config Update System for PhotoCleaner
======================================

Live-Update Mechanismus mit:
- Debouncing: Änderungen erst nach Inaktivität verarbeiten
- Batch-Updates: Mehrere Änderungen zusammenfassen
- Validation: Prüfe Werte vor Anwendung
- Callbacks: Signale für UI und Backend
- Persistence: Speichere Änderungen automatisch
"""

import logging
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
from threading import Timer

from photo_cleaner.config import AppConfig
from photo_cleaner.preset_manager import QualityPreset

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Typ der Konfigurationsänderung"""
    SLIDER_CHANGE = "slider"
    CHECKBOX_CHANGE = "checkbox"
    DROPDOWN_CHANGE = "dropdown"
    PRESET_LOADED = "preset"
    BATCH_UPDATE = "batch"


@dataclass
class ConfigChange:
    """Einzelne Konfigurationsänderung"""
    key: str  # z.B. "eye_detection_threshold"
    old_value: Any
    new_value: Any
    change_type: ChangeType
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __repr__(self) -> str:
        return f"{self.key}: {self.old_value} → {self.new_value}"


@dataclass
class ConfigSnapshot:
    """Snapshot der gesamten Konfiguration (für Undo/Redo)"""
    timestamp: datetime = field(default_factory=datetime.now)
    config: Dict[str, Any] = field(default_factory=dict)
    preset_name: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "config": self.config,
            "preset_name": self.preset_name
        }


class ConfigUpdateSystem:
    """
    Verwaltung von Konfigurations-Updates mit Debouncing und Live-Apply
    
    Features:
    - Debouncing: Updates erst nach N ms Inaktivität verarbeiten
    - Batch-Processing: Mehrere Updates zusammenfassen
    - Validation: Prüfe Werte vor Anwendung
    - Callbacks: Registriere Handler für Events
    - History: Verfolge Änderungen (für Undo/Redo)
    - Persistence: Speichere Änderungen automatisch
    """
    
    # Standard Debounce-Delay (ms)
    DEFAULT_DEBOUNCE_MS = 500
    
    # Max History-Einträge für Undo/Redo
    MAX_HISTORY = 20
    
    def __init__(self, debounce_ms: int = DEFAULT_DEBOUNCE_MS):
        """
        Initialisiere ConfigUpdateSystem
        
        Args:
            debounce_ms: Debounce-Verzögerung in Millisekunden
        """
        self.debounce_ms = debounce_ms
        self.debounce_timer: Optional[Timer] = None
        
        # Ausstehende Änderungen (noch nicht verarbeitet)
        self.pending_changes: Dict[str, ConfigChange] = {}
        
        # Verarbeitete Änderungen (History)
        self.change_history: List[ConfigChange] = []
        
        # Konfigurations-Snapshots für Undo/Redo
        self.config_history: List[ConfigSnapshot] = []
        self.history_index: int = 0
        
        # Callbacks
        self.on_change_pending: List[Callable[[ConfigChange], None]] = []
        self.on_change_applied: List[Callable[[Dict[str, ConfigChange]], None]] = []
        self.on_validation_error: List[Callable[[str, str], None]] = []
        self.on_saved: List[Callable[[str], None]] = []
        
        # Validation Regeln
        self.validation_rules: Dict[str, Callable[[Any], bool]] = {}
        
        # Aktueller Config-State
        self.current_config: Dict[str, Any] = self._load_config()
        
        # Initial Snapshot
        self._add_history_snapshot()
        
        logger.info("ConfigUpdateSystem initialisiert (debounce={debounce_ms}ms)")
    
    def _load_config(self) -> Dict[str, Any]:
        """Lade Konfiguration aus AppConfig"""
        try:
            settings = AppConfig.get_user_settings()
            config = settings.get("quality_settings", {})
            
            # Setze Defaults wenn nicht vorhanden
            defaults = {
                "eye_detection_threshold": 0.25,
                "face_confidence": 0.7,
                "blur_weight": 0.4,
                "exposure_weight": 0.3,
                "contrast_weight": 0.2,
                "noise_weight": 0.1,
                "detect_closed_eyes": True,
                "detect_blurry": True,
                "detect_underexposed": True,
                "detect_overexposed": False,
                "detect_redeye": True,
                "current_preset": "standard",
                "hide_completed_groups": False
            }
            
            # Merge mit Defaults
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value
            
            return config
        except Exception as e:
            logger.error(f"Fehler beim Laden der Konfiguration: {e}")
            return {}
    
    def _save_config(self) -> bool:
        """Speichere aktuelle Konfiguration"""
        try:
            settings = AppConfig.get_user_settings()
            settings["quality_settings"] = self.current_config
            AppConfig.set_user_settings(settings)
            
            logger.debug("Konfiguration gespeichert")
            
            # Emit Callback
            for callback in self.on_saved:
                callback("Einstellungen gespeichert")
            
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Konfiguration: {e}")
            return False
    
    def _add_history_snapshot(self) -> None:
        """Füge aktuellen State zum History hinzu"""
        snapshot = ConfigSnapshot(
            config=dict(self.current_config),
            preset_name=self.current_config.get("current_preset")
        )
        
        # Entferne zukünftige History wenn vorwärts navigiert
        if self.history_index < len(self.config_history) - 1:
            self.config_history = self.config_history[:self.history_index + 1]
        
        self.config_history.append(snapshot)
        self.history_index = len(self.config_history) - 1
        
        # Limit History-Größe
        if len(self.config_history) > self.MAX_HISTORY:
            self.config_history.pop(0)
            self.history_index = len(self.config_history) - 1
    
    def register_validation_rule(self, key: str, validator: Callable[[Any], bool]) -> None:
        """Registriere Validierungsregel
        
        Args:
            key: Config-Key
            validator: Funktion die True zurückgibt wenn gültig
        """
        self.validation_rules[key] = validator
        logger.debug(f"Validierungsregel registriert: {key}")
    
    def register_on_change_pending(self, callback: Callable[[ConfigChange], None]) -> None:
        """Registriere Callback für ausstehende Änderungen"""
        self.on_change_pending.append(callback)
    
    def register_on_change_applied(self, callback: Callable[[Dict[str, ConfigChange]], None]) -> None:
        """Registriere Callback für verarbeitete Änderungen"""
        self.on_change_applied.append(callback)
    
    def register_on_validation_error(self, callback: Callable[[str, str], None]) -> None:
        """Registriere Callback für Validierungsfehler
        
        Args:
            callback: (key, error_message) → None
        """
        self.on_validation_error.append(callback)
    
    def register_on_saved(self, callback: Callable[[str], None]) -> None:
        """Registriere Callback wenn Konfiguration gespeichert wird"""
        self.on_saved.append(callback)
    
    def request_change(self, key: str, new_value: Any, change_type: ChangeType = ChangeType.BATCH_UPDATE) -> None:
        """Fordere Konfigurationsänderung an
        
        Diese Änderung wird mit Debouncing verarbeitet.
        
        Args:
            key: Config-Key
            new_value: Neuer Wert
            change_type: Art der Änderung
        """
        old_value = self.current_config.get(key)
        
        # Erstelle ConfigChange
        change = ConfigChange(
            key=key,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type
        )
        
        # Validiere Änderung
        if not self._validate_change(change):
            logger.warning(f"Änderung validierung fehlgeschlagen: {change}")
            return
        
        # Speichere als ausstehend
        self.pending_changes[key] = change
        
        # Callback für ausstehende Änderung
        for callback in self.on_change_pending:
            callback(change)
        
        # Setze Debounce Timer neu
        self._reset_debounce_timer()
    
    def _validate_change(self, change: ConfigChange) -> bool:
        """Validiere eine einzelne Änderung"""
        # Prüfe Custom Validation Rules
        if change.key in self.validation_rules:
            validator = self.validation_rules[change.key]
            if not validator(change.new_value):
                error_msg = f"Validierung fehlgeschlagen für {change.key}: {change.new_value}"
                logger.warning(error_msg)
                
                for callback in self.on_validation_error:
                    callback(change.key, error_msg)
                
                return False
        
        # Standard Validierung (nach Range)
        if isinstance(change.new_value, (int, float)):
            if change.new_value < 0 or change.new_value > 1:
                if not change.key.endswith("_size"):  # _size kann größer sein
                    logger.warning(f"Wert außerhalb Bereich: {change.key} = {change.new_value}")
                    return False
        
        return True
    
    def _reset_debounce_timer(self) -> None:
        """Setze Debounce Timer zurück"""
        # Cancele bestehenden Timer
        if self.debounce_timer:
            self.debounce_timer.cancel()
        
        # Starte neuen Timer
        self.debounce_timer = Timer(
            self.debounce_ms / 1000.0,  # Konvertiere ms zu Sekunden
            self._apply_pending_changes
        )
        self.debounce_timer.daemon = True
        self.debounce_timer.start()
    
    def _apply_pending_changes(self) -> None:
        """Wende alle ausstehenden Änderungen an"""
        if not self.pending_changes:
            logger.debug("Keine ausstehenden Änderungen")
            return
        
        logger.info(f"Wende {len(self.pending_changes)} ausstehende Änderungen an")
        
        # Kopiere ausstehende Änderungen
        changes_to_apply = dict(self.pending_changes)
        self.pending_changes.clear()
        
        # Wende alle Änderungen an
        for key, change in changes_to_apply.items():
            self.current_config[key] = change.new_value
            self.change_history.append(change)
            logger.debug(f"Applied: {change}")
        
        # Speichere Konfiguration
        self._save_config()
        
        # Snapshot für Undo/Redo
        self._add_history_snapshot()
        
        # Callbacks für verarbeitete Änderungen
        for callback in self.on_change_applied:
            callback(changes_to_apply)
    
    def apply_immediately(self) -> None:
        """Wende ausstehende Änderungen sofort an (kein Debouncing)"""
        if self.debounce_timer:
            self.debounce_timer.cancel()
            self.debounce_timer = None
        
        self._apply_pending_changes()
    
    def load_preset(self, preset: QualityPreset) -> None:
        """Lade ein Preset und wende es an
        
        Args:
            preset: QualityPreset zum Laden
        """
        logger.info(f"Lade Preset: {preset.name}")
        
        # Erstelle Snapshot VOR Änderung
        self._add_history_snapshot()
        
        # Wende Preset-Werte an
        self.current_config["eye_detection_threshold"] = preset.eye_detection_threshold
        self.current_config["face_confidence"] = preset.face_confidence
        self.current_config["blur_weight"] = preset.blur_weight
        self.current_config["exposure_weight"] = preset.exposure_weight
        self.current_config["contrast_weight"] = preset.contrast_weight
        self.current_config["noise_weight"] = preset.noise_weight
        self.current_config["detect_closed_eyes"] = preset.detect_closed_eyes
        self.current_config["detect_blurry"] = preset.detect_blurry
        self.current_config["detect_underexposed"] = preset.detect_underexposed
        self.current_config["detect_overexposed"] = preset.detect_overexposed
        self.current_config["detect_redeye"] = preset.detect_redeye
        self.current_config["current_preset"] = preset.name.lower()
        
        # Speichere
        self._save_config()
        self._add_history_snapshot()
        
        # Callback
        changes = {"preset": ConfigChange(
            key="preset",
            old_value=None,
            new_value=preset.name,
            change_type=ChangeType.PRESET_LOADED
        )}
        for callback in self.on_change_applied:
            callback(changes)
    
    def undo(self) -> bool:
        """Gehe einen Schritt zurück in der History
        
        Returns:
            True wenn erfolgreich
        """
        if self.history_index <= 0:
            logger.warning("Nichts zum Rückgängigmachen")
            return False
        
        self.history_index -= 1
        snapshot = self.config_history[self.history_index]
        
        self.current_config = dict(snapshot.config)
        self._save_config()
        
        logger.info(f"Undo: Zur Änderung von {snapshot.timestamp}")
        return True
    
    def redo(self) -> bool:
        """Gehe einen Schritt vorwärts in der History
        
        Returns:
            True wenn erfolgreich
        """
        if self.history_index >= len(self.config_history) - 1:
            logger.warning("Nichts zum Wiederherstellen")
            return False
        
        self.history_index += 1
        snapshot = self.config_history[self.history_index]
        
        self.current_config = dict(snapshot.config)
        self._save_config()
        
        logger.info(f"Redo: Zur Änderung von {snapshot.timestamp}")
        return True
    
    def get_config(self, key: Optional[str] = None, default: Any = None) -> Any:
        """Hole aktuellen Config-Wert(e).
        
        Args:
            key: Spezifischer Key, oder None für ganzes Dict
            default: Rückgabewert, falls Key nicht gesetzt ist
        
        Returns:
            Config-Wert oder ganzes Dict
        """
        if key is None:
            return dict(self.current_config)
        return self.current_config.get(key, default)
    
    def get_history(self, limit: int = 10) -> List[ConfigChange]:
        """Hole Änderungs-History
        
        Args:
            limit: Maximale Anzahl von Einträgen
        
        Returns:
            Liste der letzten Änderungen
        """
        return self.change_history[-limit:]
    
    def export_config(self, output_path: Path) -> bool:
        """Exportiere Konfiguration zu JSON
        
        Args:
            output_path: Ziel-Pfad
        
        Returns:
            True wenn erfolgreich
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.current_config, f, indent=2, ensure_ascii=False)
            logger.info(f"Konfiguration exportiert nach {output_path}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Export: {e}")
            return False
    
    def import_config(self, input_path: Path) -> bool:
        """Importiere Konfiguration aus JSON
        
        Args:
            input_path: Quell-Pfad
        
        Returns:
            True wenn erfolgreich
        """
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Validiere alle Werte
            for key, value in config.items():
                change = ConfigChange(
                    key=key,
                    old_value=self.current_config.get(key),
                    new_value=value,
                    change_type=ChangeType.BATCH_UPDATE
                )
                if not self._validate_change(change):
                    logger.warning(f"Import-Validierung fehlgeschlagen für {key}")
                    return False
            
            # Wende an
            self.current_config.update(config)
            self._save_config()
            self._add_history_snapshot()
            
            logger.info(f"Konfiguration importiert von {input_path}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Import: {e}")
            return False
    
    def reset_to_defaults(self) -> None:
        """Setze Konfiguration auf Defaults zurück"""
        logger.warning("Setze Konfiguration auf Defaults zurück")
        
        self.current_config = {
            "eye_detection_threshold": 0.25,
            "face_confidence": 0.7,
            "blur_weight": 0.4,
            "exposure_weight": 0.3,
            "contrast_weight": 0.2,
            "noise_weight": 0.1,
            "detect_closed_eyes": True,
            "detect_blurry": True,
            "detect_underexposed": True,
            "detect_overexposed": False,
            "detect_redeye": True,
            "current_preset": "standard"
        }
        
        self._save_config()
        self._add_history_snapshot()


# Convenience function
def get_config_update_system() -> ConfigUpdateSystem:
    """Singleton-Pattern für ConfigUpdateSystem"""
    if not hasattr(get_config_update_system, "_instance"):
        get_config_update_system._instance = ConfigUpdateSystem()
    return get_config_update_system._instance


if __name__ == "__main__":
    # Test-Modus
    logging.basicConfig(level=logging.DEBUG)
    
    system = ConfigUpdateSystem(debounce_ms=200)
    
    # Test Callbacks
    def on_change(change: ConfigChange):
        print(f"Änderung ausstehend: {change}")
    
    def on_applied(changes: Dict[str, ConfigChange]):
        print(f"Änderungen angewendet: {changes}")
    
    system.register_on_change_pending(on_change)
    system.register_on_change_applied(on_applied)
    
    # Test Änderungen
    print("Teste Änderungen...")
    system.request_change("blur_weight", 0.5, ChangeType.SLIDER_CHANGE)
    system.request_change("exposure_weight", 0.35, ChangeType.SLIDER_CHANGE)
    system.request_change("detect_closed_eyes", False, ChangeType.CHECKBOX_CHANGE)
    
    # Warte auf Debounce
    import time
    time.sleep(1)
    
    print(f"\nAktueller Config: {system.get_config()}")
