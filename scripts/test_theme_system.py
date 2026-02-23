#!/usr/bin/env python3
"""Test the PhotoCleaner Theme System.

Tests:
1. Theme switching functionality
2. StyleSheet generation
3. Color constants
4. ThemeManager singleton
5. Settings persistence

Run with:
    python -m pytest tests/test_theme_system.py -v
Or:
    python scripts/test_theme_system.py
"""
import sys
import json
from pathlib import Path
from tempfile import TemporaryDirectory

# Test setup
def test_theme_colors():
    """Test that theme colors are properly defined."""
    from photo_cleaner.theme import THEMES, get_theme_colors
    
    print("\n✓ Testing theme colors...")
    
    # Check both themes exist
    assert "dark" in THEMES, "Dark theme not defined"
    assert "light" in THEMES, "Light theme not defined"
    
    # Check required colors
    required_colors = [
        "window", "window_text", "base", "text", "button",
        "button_text", "highlight", "border", "input_bg"
    ]
    
    for theme_name, theme in THEMES.items():
        for color in required_colors:
            assert color in theme, f"Color '{color}' missing in {theme_name} theme"
            assert theme[color].startswith("#"), f"Color value must be hex: {color}"
    
    # Test color retrieval
    dark_colors = get_theme_colors("dark")
    light_colors = get_theme_colors("light")
    
    assert dark_colors["window"] == "#1a1a1a", "Dark theme window color incorrect"
    assert light_colors["window"] == "#f5f5f5", "Light theme window color incorrect"
    
    print("  ✓ All color definitions are correct")
    return True


def test_stylesheet_generation():
    """Test that StyleSheet generation works."""
    from photo_cleaner.theme import generate_stylesheet
    
    print("\n✓ Testing StyleSheet generation...")
    
    # Generate stylesheets
    dark_ss = generate_stylesheet("dark")
    light_ss = generate_stylesheet("light")
    
    assert len(dark_ss) > 500, "Dark stylesheet too short"
    assert len(light_ss) > 500, "Light stylesheet too short"
    
    # Check key elements
    for ss in [dark_ss, light_ss]:
        assert "QMainWindow" in ss, "Missing QMainWindow styling"
        assert "QPushButton" in ss, "Missing QPushButton styling"
        assert "QLineEdit" in ss, "Missing QLineEdit styling"
        assert "QScrollBar" in ss, "Missing QScrollBar styling"
    
    # Dark and light should be different
    assert dark_ss != light_ss, "Dark and light stylesheets should differ"
    
    print(f"  ✓ Dark theme stylesheet: {len(dark_ss)} chars")
    print(f"  ✓ Light theme stylesheet: {len(light_ss)} chars")
    return True


def test_color_constants():
    """Test color constants module."""
    from photo_cleaner.ui.color_constants import (
        get_status_colors,
        get_quality_colors,
        get_semantic_colors,
        get_component_colors,
    )
    
    print("\n✓ Testing color constants...")
    
    # Test status colors
    status = get_status_colors()
    assert status["KEEP"] == "#4CAF50", "Keep color incorrect"
    assert status["DELETE"] == "#F44336", "Delete color incorrect"
    print("  ✓ Status colors correct")
    
    # Test quality colors
    quality = get_quality_colors()
    assert "high" in quality, "Missing high quality color"
    assert "medium" in quality, "Missing medium quality color"
    assert "low" in quality, "Missing low quality color"
    print("  ✓ Quality colors correct")
    
    # Test semantic colors
    semantic = get_semantic_colors()
    assert "success" in semantic, "Missing success color"
    assert "error" in semantic, "Missing error color"
    print("  ✓ Semantic colors correct")
    
    # Test component colors
    component = get_component_colors("dark")
    assert "bg_main" in component, "Missing background color"
    assert "border" in component, "Missing border color"
    print("  ✓ Component colors correct")
    
    return True


def test_theme_manager():
    """Test ThemeManager singleton."""
    print("\n✓ Testing ThemeManager...")
    
    # Skip if QApplication not available
    try:
        from PySide6.QtWidgets import QApplication
        from photo_cleaner.ui.theme_manager import ThemeManager
        
        # Get instances
        m1 = ThemeManager.instance()
        m2 = ThemeManager.instance()
        
        # Should be same object (singleton)
        assert m1 is m2, "ThemeManager should be singleton"
        print("  ✓ ThemeManager is singleton")
        
        # Test get_theme
        theme = m1.get_current_theme()
        assert theme in ["dark", "light"], f"Invalid theme: {theme}"
        print(f"  ✓ Current theme: {theme}")
        
        return True
    except ImportError as e:
        print(f"  ⚠ Skipped (PySide6 not available): {e}")
        return True


def test_settings_persistence():
    """Test saving/loading theme from settings."""
    from photo_cleaner.theme import save_theme_to_settings, load_theme_from_settings
    
    print("\n✓ Testing settings persistence...")
    
    with TemporaryDirectory() as tmpdir:
        settings_path = Path(tmpdir) / "settings.json"
        
        # Save dark theme
        success = save_theme_to_settings(settings_path, "dark")
        assert success, "Failed to save dark theme"
        
        # Load it back
        theme = load_theme_from_settings(settings_path)
        assert theme == "dark", f"Loaded theme should be dark, got {theme}"
        
        # Check file content
        with open(settings_path, 'r') as f:
            data = json.load(f)
            assert data["theme"] == "dark", "Settings file incorrect"
        
        print("  ✓ Dark theme saved and loaded correctly")
        
        # Save light theme
        success = save_theme_to_settings(settings_path, "light")
        assert success, "Failed to save light theme"
        
        # Load it back
        theme = load_theme_from_settings(settings_path)
        assert theme == "light", f"Loaded theme should be light, got {theme}"
        
        print("  ✓ Light theme saved and loaded correctly")
        
        return True


def test_palette_generation():
    """Test QPalette generation from themes."""
    print("\n✓ Testing QPalette generation...")
    
    try:
        from PySide6.QtGui import QPalette
        from photo_cleaner.theme import apply_theme_to_palette
        
        # Generate dark palette
        dark_pal = apply_theme_to_palette("dark")
        assert isinstance(dark_pal, QPalette), "Should return QPalette"
        
        # Generate light palette
        light_pal = apply_theme_to_palette("light")
        assert isinstance(light_pal, QPalette), "Should return QPalette"
        
        print("  ✓ Dark palette generated successfully")
        print("  ✓ Light palette generated successfully")
        return True
    except ImportError:
        print("  ⚠ Skipped (PySide6 not available)")
        return True


def main():
    """Run all tests."""
    print("=" * 80)
    print("PHOTOCLEANER THEME SYSTEM TESTS")
    print("=" * 80)
    
    tests = [
        test_theme_colors,
        test_stylesheet_generation,
        test_color_constants,
        test_palette_generation,
        test_theme_manager,
        test_settings_persistence,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"✗ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n✗ {test.__name__} FAILED with exception:")
            print(f"  {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
