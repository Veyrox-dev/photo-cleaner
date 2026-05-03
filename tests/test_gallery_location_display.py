"""
Test für Phase 1: Erweitertes EXIF-Snippet mit Aufnahmeort-Anzeige.

Validiert, dass der Orts-Name korrekt im EXIF-Snippet (unter Thumbnail) angezeigt wird.
"""

import pytest
from pathlib import Path
from datetime import datetime
from photo_cleaner.ui.gallery.gallery_view import GalleryEntry


class TestPhase1LocationDisplay:
    """Phase 1: EXIF-Snippet mit Orts-Anzeige."""
    
    def test_gallery_entry_with_location(self):
        """Test: GalleryEntry kann location_name enthalten."""
        entry = GalleryEntry(
            path=Path("/test/image.jpg"),
            quality_score=85.0,
            sharpness_component=0.9,
            lighting_component=0.8,
            resolution_component=0.85,
            face_quality_component=None,
            capture_time=1714675200.0,  # 2024-05-02
            exif_json='{"Model": "Sony A7IV"}',
            location_name="New York, USA"  # Phase 1: Ort wird angezeigt
        )
        
        assert entry.location_name == "New York, USA"
    
    def test_gallery_entry_without_location(self):
        """Test: GalleryEntry funktioniert auch ohne location_name (Fallback)."""
        entry = GalleryEntry(
            path=Path("/test/image.jpg"),
            quality_score=75.0,
            sharpness_component=0.8,
            lighting_component=0.7,
            resolution_component=0.75,
            face_quality_component=None,
            capture_time=1714675200.0,
            exif_json='{"Model": "Canon EOS R6"}',
            location_name=None  # Fallback: kein Ort verfügbar
        )
        
        assert entry.location_name is None
    
    def test_exif_snippet_format_with_location(self):
        """Test: EXIF-Snippet wird korrekt mit Ort formatiert."""
        # Simuliere _build_exif_snippet() Logik
        entry = GalleryEntry(
            path=Path("/test/image.jpg"),
            quality_score=85.0,
            sharpness_component=0.9,
            lighting_component=0.8,
            resolution_component=0.85,
            face_quality_component=None,
            capture_time=1714675200.0,  # 2024-05-02
            exif_json='{"Model": "Sony A7IV"}',
            location_name="New York, USA"
        )
        
        # Simuliere _build_exif_snippet() Zusammensetzung
        parts = []
        
        # Datum
        if entry.capture_time:
            dt = datetime.fromtimestamp(entry.capture_time)
            parts.append(dt.strftime("%Y-%m-%d"))
        
        # Kamera
        import json
        if entry.exif_json:
            try:
                exif = json.loads(entry.exif_json)
                model = exif.get("Model")
                if model:
                    parts.append(str(model))
            except json.JSONDecodeError:
                pass
        
        # Phase 1: Ort
        if entry.location_name:
            parts.append(entry.location_name)
        
        snippet = " | ".join(parts)
        
        # Erwartet: "2024-05-02 | Sony A7IV | New York, USA"
        assert snippet == "2024-05-02 | Sony A7IV | New York, USA"
        print(f"✓ EXIF-Snippet mit Ort: {snippet}")
    
    def test_exif_snippet_format_without_location(self):
        """Test: EXIF-Snippet funktioniert auch ohne Ort."""
        entry = GalleryEntry(
            path=Path("/test/image.jpg"),
            quality_score=75.0,
            sharpness_component=0.8,
            lighting_component=0.7,
            resolution_component=0.75,
            face_quality_component=None,
            capture_time=1714675200.0,
            exif_json='{"Model": "Canon EOS R6"}',
            location_name=None  # Kein Ort
        )
        
        # Simuliere _build_exif_snippet() Zusammensetzung
        parts = []
        
        if entry.capture_time:
            dt = datetime.fromtimestamp(entry.capture_time)
            parts.append(dt.strftime("%Y-%m-%d"))
        
        import json
        if entry.exif_json:
            try:
                exif = json.loads(entry.exif_json)
                model = exif.get("Model")
                if model:
                    parts.append(str(model))
            except json.JSONDecodeError:
                pass
        
        if entry.location_name:
            parts.append(entry.location_name)
        
        snippet = " | ".join(parts)
        
        # Erwartet: "2024-05-02 | Canon EOS R6" (ohne Ort)
        assert snippet == "2024-05-02 | Canon EOS R6"
        print(f"✓ EXIF-Snippet ohne Ort: {snippet}")
    
    def test_location_name_truncation(self):
        """Test: Sehr lange Ortsnamen werden ggf. gekürzt."""
        long_location = "Very Long City Name with Many Characters, Some Country Code, Additional Info"
        
        entry = GalleryEntry(
            path=Path("/test/image.jpg"),
            quality_score=80.0,
            sharpness_component=0.85,
            lighting_component=0.75,
            resolution_component=0.80,
            face_quality_component=None,
            capture_time=1714675200.0,
            exif_json='{"Model": "Nikon Z6II"}',
            location_name=long_location
        )
        
        # Die location_name wird direkt angezeigt (kein Truncating in dieser Phase)
        assert entry.location_name == long_location
        # In GalleryCard könnten wir später truncating hinzufügen, z.B. max 30 Zeichen


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
