"""
Unit Tests for PresetManager

Tests preset creation, loading, saving, and management.
"""

import json
import tempfile
from pathlib import Path
from unittest import TestCase, mock

import pytest

from photo_cleaner.preset_manager import (
    PresetManager,
    QualityPreset,
)


class TestQualityPreset(TestCase):
    """Tests for QualityPreset data class."""

    def test_create_preset(self):
        """Test creating a quality preset."""
        preset = QualityPreset(
            name="Test Preset",
            description="Test Description",
            eye_detection_mode=2,
            eye_detection_threshold=0.7,
            face_confidence=0.8,
            blur_weight=0.25,
            exposure_weight=0.25,
            contrast_weight=0.25,
            noise_weight=0.25,
        )

        assert preset.name == "Test Preset"
        assert preset.eye_detection_mode == 2
        assert preset.eye_detection_threshold == 0.7

    def test_preset_from_dict(self):
        """Test creating preset from dictionary."""
        data = {
            "name": "Custom",
            "description": "Custom preset",
            "eye_detection_mode": 3,
            "eye_detection_threshold": 0.75,
            "face_confidence": 0.85,
            "blur_weight": 0.3,
            "exposure_weight": 0.3,
            "contrast_weight": 0.2,
            "noise_weight": 0.2,
        }
        preset = QualityPreset(**data)
        assert preset.name == "Custom"
        assert preset.blur_weight == 0.3

    def test_preset_to_dict(self):
        """Test converting preset to dictionary."""
        preset = QualityPreset(
            name="Test",
            description="Test",
            eye_detection_mode=1,
            eye_detection_threshold=0.5,
            face_confidence=0.6,
        )
        preset_dict = vars(preset)
        assert preset_dict["name"] == "Test"


class TestPresetManager(TestCase):
    """Tests for PresetManager."""

    def setUp(self):
        """Set up preset manager with temp directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)
        self.manager = PresetManager()

    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_preset_manager_initialization(self):
        """Test preset manager initializes correctly."""
        assert self.manager is not None
        assert "standard" in self.manager.list_presets()

    def test_get_default_presets(self):
        """Test getting default presets."""
        preset_names = self.manager.list_presets()
        assert len(preset_names) > 0
        # Should have at least standard preset
        assert "standard" in preset_names
        
        # Get actual preset objects
        for name in preset_names:
            preset = self.manager.get_preset(name)
            assert preset is not None
            assert hasattr(preset, "name")
