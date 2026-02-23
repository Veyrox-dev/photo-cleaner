#!/usr/bin/env python3
"""Test script for i18n and theme system integration."""
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_i18n():
    """Test i18n module."""
    from photo_cleaner.i18n import (
        set_language, get_language, translate as t,
        get_available_languages,
        load_language_from_settings, save_language_to_settings
    )

    set_language("de")
    assert get_language() == "de", "Language should be 'de'"

    set_language("en")
    assert get_language() == "en", "Language should be 'en'"

    result = t("import", "de")
    assert result.endswith("Import"), f"Expected translated German text, got {result}"

    result = t("import", "en")
    assert result.endswith("Import"), f"Expected translated English text, got {result}"

    langs = get_available_languages()
    assert "de" in langs and "en" in langs, "Should have de and en"

    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "test_settings.json"
        save_language_to_settings(settings_file, "en")
        load_language_from_settings(settings_file)
        assert get_language() == "en", "Should load language from settings"

def test_theme():
    """Test theme module."""
    from photo_cleaner.theme import (
        set_theme, get_theme, get_theme_colors,
        apply_theme_to_palette,
        load_theme_from_settings, save_theme_to_settings
    )
    from PySide6.QtGui import QPalette

    set_theme("dark")
    assert get_theme() == "dark", "Theme should be 'dark'"

    set_theme("light")
    assert get_theme() == "light", "Theme should be 'light'"

    colors = get_theme_colors("dark")
    assert "window" in colors, "Should have window color"

    colors = get_theme_colors("light")
    assert "window" in colors, "Should have window color"

    set_theme("dark")
    palette = apply_theme_to_palette()
    assert isinstance(palette, QPalette), "Should return QPalette"

    set_theme("light")
    palette = apply_theme_to_palette()
    assert isinstance(palette, QPalette), "Should return QPalette"

    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "test_settings.json"
        save_theme_to_settings(settings_file, "light")
        load_theme_from_settings(settings_file)
        assert get_theme() == "light", "Should load theme from settings"

def test_imports_in_modern_window():
    """Test that modern_window can import the new modules."""
    project_root = Path(__file__).resolve().parents[2]
    modern_window_path = project_root / "src" / "photo_cleaner" / "ui" / "modern_window.py"
    content = modern_window_path.read_text(encoding="utf-8")

    assert "def _change_language" in content
    assert "def _change_theme" in content

if __name__ == "__main__":
    print("=" * 60)
    print("PhotoCleaner i18n/Theme Integration Tests")
    print("=" * 60)
    print()
    
    results = []
    results.append(("i18n", test_i18n()))
    results.append(("theme", test_theme()))
    results.append(("modern_window", test_imports_in_modern_window()))
    
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print("{:20} {}".format(name, status))
    
    all_passed = all(passed for _, passed in results)
    print("=" * 60)
    if all_passed:
        print("[PASS] All tests passed!")
        sys.exit(0)
    else:
        print("[FAIL] Some tests failed")
        sys.exit(1)
