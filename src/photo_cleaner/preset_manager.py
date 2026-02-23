"""
Preset Manager for PhotoCleaner Quality Settings
================================================

Verwaltet vordefinierte Presets für verschiedene Use-Cases:
- Standard: Ausgewogene Einstellungen für allgemeine Nutzung
- Streng: Hohe Anforderungen, nur beste Bilder
- Locker: Niedrige Anforderungen, akzeptiert mehr Variationen
- Portrait: Optimiert für Portraits (Fokus auf Gesichter)
- Landschaft: Optimiert für Landschafts-/Architekturfotos
- Benutzerdefiniert: Nutzer-definierte Einstellungen

Persistente Speicherung in settings.json
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
from photo_cleaner.config import AppConfig

logger = logging.getLogger(__name__)


@dataclass
class QualityPreset:
    """
    Qualitäts-Preset für Eye-Detection und Bildqualität
    
    Attributes:
        name: Preset-Name (z.B. "Standard", "Streng")
        description: Kurze Beschreibung des Presets
        
        Eye-Detection Settings:
        eye_detection_mode: 1 (Haar), 2 (dlib), oder 3 (MediaPipe)
        eye_detection_threshold: Schwelle für Augenerkennung (0.0-1.0)
        face_confidence: Minimum Konfidenz für Gesichtserkennung (0.0-1.0)
        min_eye_size: Minimale Augengröße in Pixeln
        
        Quality Weights (Summe sollte ~1.0 sein):
        blur_weight: Gewichtung für Schärfe (0.0-1.0)
        exposure_weight: Gewichtung für Belichtung (0.0-1.0)
        contrast_weight: Gewichtung für Kontrast (0.0-1.0)
        noise_weight: Gewichtung für Rauscharmut (0.0-1.0)
        
        Detection Flags:
        detect_closed_eyes: Geschlossene Augen erkennen
        detect_blurry: Unscharfe Bilder erkennen
        detect_underexposed: Unterbelichtete Bilder erkennen
        detect_overexposed: Überbelichtete Bilder erkennen
        detect_redeye: Rote-Augen-Effekt erkennen
        
        is_builtin: Vordefiniertes Preset (nur lesbar)
    """
    name: str
    description: str
    
    # Eye-Detection Settings
    eye_detection_mode: int = 1
    eye_detection_threshold: float = 0.25
    face_confidence: float = 0.7
    min_eye_size: int = 50
    
    # Quality Weights
    blur_weight: float = 0.4
    exposure_weight: float = 0.3
    contrast_weight: float = 0.2
    noise_weight: float = 0.1
    
    # Detection Flags
    detect_closed_eyes: bool = True
    detect_blurry: bool = True
    detect_underexposed: bool = True
    detect_overexposed: bool = False
    detect_redeye: bool = True
    
    # System
    is_builtin: bool = True
    user_editable: bool = True
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dictionary für JSON-Speicherung"""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> "QualityPreset":
        """Erstelle Preset aus Dictionary"""
        return QualityPreset(**data)
    
    def validate(self) -> List[str]:
        """Validiere Preset-Einstellungen
        
        Returns:
            Liste von Validierungs-Fehlern (leer wenn valid)
        """
        errors = []
        
        # Eye-Detection Mode
        if self.eye_detection_mode not in [1, 2, 3]:
            errors.append(f"Invalid eye_detection_mode: {self.eye_detection_mode} (expected 1, 2, or 3)")
        
        # Thresholds (0.0 - 1.0)
        if not (0.0 <= self.eye_detection_threshold <= 1.0):
            errors.append(f"eye_detection_threshold out of range: {self.eye_detection_threshold}")
        if not (0.0 <= self.face_confidence <= 1.0):
            errors.append(f"face_confidence out of range: {self.face_confidence}")
        
        # Eye size
        if self.min_eye_size < 0:
            errors.append(f"min_eye_size must be positive: {self.min_eye_size}")
        
        # Weights (0.0 - 1.0)
        for weight_name in ["blur_weight", "exposure_weight", "contrast_weight", "noise_weight"]:
            value = getattr(self, weight_name)
            if not (0.0 <= value <= 1.0):
                errors.append(f"{weight_name} out of range: {value}")
        
        # Check weight sum (should be ~1.0)
        weight_sum = (self.blur_weight + self.exposure_weight + 
                     self.contrast_weight + self.noise_weight)
        if not (0.8 <= weight_sum <= 1.2):
            logger.warning(f"Quality weights sum to {weight_sum:.2f} (expected ~1.0)")
        
        return errors


class PresetManager:
    """Verwaltet Quality-Presets"""
    
    # Vordefinierte Built-In Presets
    BUILTIN_PRESETS = {
        "standard": QualityPreset(
            name="Standard",
            description="Ausgewogene Einstellungen für allgemeine Nutzung",
            eye_detection_mode=2,
            eye_detection_threshold=0.25,
            face_confidence=0.7,
            min_eye_size=50,
            blur_weight=0.4,
            exposure_weight=0.3,
            contrast_weight=0.2,
            noise_weight=0.1,
            detect_closed_eyes=True,
            detect_blurry=True,
            detect_underexposed=True,
            detect_overexposed=False,
            detect_redeye=True,
            is_builtin=True,
            user_editable=False
        ),
        "streng": QualityPreset(
            name="Streng",
            description="Hohe Anforderungen, nur die besten Bilder akzeptiert",
            eye_detection_mode=3,
            eye_detection_threshold=0.35,
            face_confidence=0.85,
            min_eye_size=60,
            blur_weight=0.5,
            exposure_weight=0.25,
            contrast_weight=0.15,
            noise_weight=0.1,
            detect_closed_eyes=True,
            detect_blurry=True,
            detect_underexposed=True,
            detect_overexposed=True,
            detect_redeye=True,
            is_builtin=True,
            user_editable=False
        ),
        "locker": QualityPreset(
            name="Locker",
            description="Niedrige Anforderungen, akzeptiert mehr Variationen",
            eye_detection_mode=1,
            eye_detection_threshold=0.15,
            face_confidence=0.5,
            min_eye_size=30,
            blur_weight=0.3,
            exposure_weight=0.35,
            contrast_weight=0.25,
            noise_weight=0.1,
            detect_closed_eyes=False,
            detect_blurry=False,
            detect_underexposed=False,
            detect_overexposed=False,
            detect_redeye=False,
            is_builtin=True,
            user_editable=False
        ),
        "portrait": QualityPreset(
            name="Portrait",
            description="Optimiert für Portraits (Fokus auf Gesichter und Augen)",
            eye_detection_mode=3,
            eye_detection_threshold=0.3,
            face_confidence=0.8,
            min_eye_size=40,
            blur_weight=0.3,
            exposure_weight=0.4,
            contrast_weight=0.2,
            noise_weight=0.1,
            detect_closed_eyes=True,
            detect_blurry=True,
            detect_underexposed=True,
            detect_overexposed=False,
            detect_redeye=True,
            is_builtin=True,
            user_editable=False
        ),
        "landschaft": QualityPreset(
            name="Landschaft",
            description="Optimiert für Landschafts- und Architekturfotos",
            eye_detection_mode=1,
            eye_detection_threshold=0.2,
            face_confidence=0.6,
            min_eye_size=40,
            blur_weight=0.5,
            exposure_weight=0.25,
            contrast_weight=0.15,
            noise_weight=0.1,
            detect_closed_eyes=False,
            detect_blurry=True,
            detect_underexposed=False,
            detect_overexposed=True,
            detect_redeye=False,
            is_builtin=True,
            user_editable=False
        )
    }
    
    def __init__(self):
        """Initialisiere PresetManager"""
        self.presets: Dict[str, QualityPreset] = {}
        self.current_preset: Optional[str] = None
        
        # Lade eingebaute Presets
        for key, preset in self.BUILTIN_PRESETS.items():
            self.presets[key] = preset
        
        # Lade benutzerdefinierte Presets aus settings
        self._load_user_presets()
        
        logger.info(f"PresetManager initialisiert: {len(self.presets)} Presets geladen")
    
    def _load_user_presets(self):
        """Lade benutzerdefinierte Presets aus settings.json"""
        try:
            user_presets = AppConfig.get_user_settings().get("quality_presets", {})
            for key, data in user_presets.items():
                if key not in self.BUILTIN_PRESETS:  # Nicht über Built-In überschreiben
                    try:
                        preset = QualityPreset.from_dict(data)
                        preset.is_builtin = False
                        self.presets[key] = preset
                        logger.debug(f"Benutzer-Preset geladen: {key}")
                    except Exception as e:
                        logger.warning(f"Fehler beim Laden von Preset {key}: {e}")
        except Exception as e:
            logger.warning(f"Fehler beim Laden von Benutzer-Presets: {e}")
    
    def _save_user_presets(self):
        """Speichere benutzerdefinierte Presets in settings.json"""
        try:
            user_presets = {}
            for key, preset in self.presets.items():
                if not preset.is_builtin:
                    user_presets[key] = preset.to_dict()
            
            settings = AppConfig.get_user_settings()
            settings["quality_presets"] = user_presets
            AppConfig.set_user_settings(settings)
            logger.debug(f"Benutzer-Presets gespeichert: {len(user_presets)} Presets")
        except Exception as e:
            logger.error(f"Fehler beim Speichern von Benutzer-Presets: {e}")
    
    def get_preset(self, name: str) -> Optional[QualityPreset]:
        """Hole ein Preset nach Name"""
        return self.presets.get(name)
    
    def list_presets(self) -> List[str]:
        """Gib Liste aller verfügbaren Preset-Namen"""
        return list(self.presets.keys())
    
    def list_presets_detailed(self) -> Dict[str, dict]:
        """Gib detaillierte Info über alle Presets"""
        return {
            key: {
                "name": preset.name,
                "description": preset.description,
                "is_builtin": preset.is_builtin,
                "user_editable": preset.user_editable
            }
            for key, preset in self.presets.items()
        }
    
    def create_preset(self, key: str, preset: QualityPreset) -> bool:
        """Erstelle neues Benutzer-Preset
        
        Args:
            key: Eindeutiger Schlüssel (z.B. "mein_preset")
            preset: QualityPreset Objekt
        
        Returns:
            True wenn erfolgreich, False wenn Fehler
        """
        if key in self.BUILTIN_PRESETS:
            logger.warning(f"Kann Built-In Preset nicht überschreiben: {key}")
            return False
        
        if key in self.presets and self.presets[key].is_builtin:
            logger.warning(f"Kann Built-In Preset nicht überschreiben: {key}")
            return False
        
        # Validiere Preset
        errors = preset.validate()
        if errors:
            logger.error(f"Preset-Validierung fehlgeschlagen: {errors}")
            return False
        
        preset.is_builtin = False
        self.presets[key] = preset
        self._save_user_presets()
        logger.info(f"Neues Preset erstellt: {key}")
        return True
    
    def update_preset(self, key: str, preset: QualityPreset) -> bool:
        """Aktualisiere bestehendes Preset
        
        Args:
            key: Preset-Schlüssel
            preset: Aktualisiertes Preset
        
        Returns:
            True wenn erfolgreich
        """
        if key not in self.presets:
            logger.warning(f"Preset nicht gefunden: {key}")
            return False
        
        existing = self.presets[key]
        if existing.is_builtin and not existing.user_editable:
            logger.warning(f"Kann Built-In Preset nicht editieren: {key}")
            return False
        
        errors = preset.validate()
        if errors:
            logger.error(f"Preset-Validierung fehlgeschlagen: {errors}")
            return False
        
        self.presets[key] = preset
        if not preset.is_builtin:
            self._save_user_presets()
        
        logger.info(f"Preset aktualisiert: {key}")
        return True
    
    def delete_preset(self, key: str) -> bool:
        """Lösche Benutzer-Preset
        
        Args:
            key: Preset-Schlüssel
        
        Returns:
            True wenn erfolgreich
        """
        if key not in self.presets:
            logger.warning(f"Preset nicht gefunden: {key}")
            return False
        
        preset = self.presets[key]
        if preset.is_builtin:
            logger.warning(f"Kann Built-In Preset nicht löschen: {key}")
            return False
        
        del self.presets[key]
        self._save_user_presets()
        logger.info(f"Preset gelöscht: {key}")
        return True
    
    def duplicate_preset(self, source_key: str, new_key: str) -> bool:
        """Dupliziere ein Preset
        
        Args:
            source_key: Quell-Preset
            new_key: Name des neuen Presets
        
        Returns:
            True wenn erfolgreich
        """
        if source_key not in self.presets:
            logger.warning(f"Quell-Preset nicht gefunden: {source_key}")
            return False
        
        source = self.presets[source_key]
        
        # Erstelle Kopie mit neuem Namen
        new_preset = QualityPreset(
            name=new_key,
            description=f"Kopie von {source.name}",
            eye_detection_mode=source.eye_detection_mode,
            eye_detection_threshold=source.eye_detection_threshold,
            face_confidence=source.face_confidence,
            min_eye_size=source.min_eye_size,
            blur_weight=source.blur_weight,
            exposure_weight=source.exposure_weight,
            contrast_weight=source.contrast_weight,
            noise_weight=source.noise_weight,
            detect_closed_eyes=source.detect_closed_eyes,
            detect_blurry=source.detect_blurry,
            detect_underexposed=source.detect_underexposed,
            detect_overexposed=source.detect_overexposed,
            detect_redeye=source.detect_redeye,
            is_builtin=False,
            user_editable=True
        )
        
        return self.create_preset(new_key, new_preset)
    
    def export_presets(self, output_path: Path) -> bool:
        """Exportiere alle Presets zu JSON-Datei
        
        Args:
            output_path: Ziel-Pfad
        
        Returns:
            True wenn erfolgreich
        """
        try:
            data = {
                key: preset.to_dict()
                for key, preset in self.presets.items()
            }
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Presets exportiert nach {output_path}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Export von Presets: {e}")
            return False
    
    def import_presets(self, input_path: Path) -> bool:
        """Importiere Presets aus JSON-Datei
        
        Args:
            input_path: Quell-Pfad
        
        Returns:
            True wenn erfolgreich
        """
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            count = 0
            for key, preset_data in data.items():
                if key not in self.BUILTIN_PRESETS:
                    try:
                        preset = QualityPreset.from_dict(preset_data)
                        if self.create_preset(key, preset):
                            count += 1
                    except Exception as e:
                        logger.warning(f"Fehler beim Importieren von {key}: {e}")
            
            logger.info(f"Presets importiert: {count}/{len(data)}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Import von Presets: {e}")
            return False
    
    def reset_to_defaults(self) -> None:
        """Setze alle Presets auf Standard zurück"""
        # Lösche alle Benutzer-Presets
        user_keys = [k for k, p in self.presets.items() if not p.is_builtin]
        for key in user_keys:
            del self.presets[key]
        
        # Lade Standard Presets neu
        self.presets.clear()
        for key, preset in self.BUILTIN_PRESETS.items():
            self.presets[key] = preset
        
        self._save_user_presets()
        logger.info("Presets auf Standard zurückgesetzt")


# Convenience function für Singleton
def get_preset_manager() -> PresetManager:
    """Singleton-Pattern für PresetManager"""
    if not hasattr(get_preset_manager, "_instance"):
        get_preset_manager._instance = PresetManager()
    return get_preset_manager._instance


if __name__ == "__main__":
    # Test-Modus
    import sys
    logging.basicConfig(level=logging.INFO)
    
    manager = PresetManager()
    
    print("Verfügbare Presets:")
    for key, info in manager.list_presets_detailed().items():
        print(f"  • {info['name']}: {info['description']}")
        print(f"    Built-In: {info['is_builtin']}")
    
    print("\nStandard Preset:")
    preset = manager.get_preset("standard")
    if preset:
        print(f"  Name: {preset.name}")
        print(f"  Eye Detection Mode: {preset.eye_detection_mode}")
        print(f"  Face Confidence: {preset.face_confidence}")
        print(f"  Blur Weight: {preset.blur_weight}")
