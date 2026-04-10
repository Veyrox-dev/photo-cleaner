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
        get_available_languages, TRANSLATIONS,
        load_language_from_settings, save_language_to_settings
    )

    set_language("de")
    assert get_language() == "de", "Language should be 'de'"

    set_language("en")
    assert get_language() == "en", "Language should be 'en'"

    set_language("fr")
    assert get_language() == "fr", "Language should be 'fr'"

    set_language("es")
    assert get_language() == "es", "Language should be 'es'"

    set_language("nl")
    assert get_language() == "nl", "Language should be 'nl'"

    set_language("it")
    assert get_language() == "it", "Language should be 'it'"

    result = t("import", "de")
    assert result.endswith("Import"), f"Expected translated German text, got {result}"

    result = t("import", "en")
    assert result.endswith("Import"), f"Expected translated English text, got {result}"

    langs = get_available_languages()
    assert "de" in langs and "en" in langs, "Should have de and en"
    assert "fr" in langs and "es" in langs and "nl" in langs, "Should have fr, es and nl"
    assert "it" in langs, "Should have it (Italian)"

    # New languages must be technically complete (auto-synced against EN).
    en_keys = set(TRANSLATIONS["en"].keys())
    for code in ("fr", "es", "nl", "it"):
        locale_keys = set(TRANSLATIONS[code].keys())
        missing = en_keys - locale_keys
        assert not missing, f"Missing keys in {code}: {len(missing)}"

    # Fallback should still work for unknown keys.
    result = t("import", "fr")
    assert result == "Importer", f"Expected translated fr text, got {result}"
    assert t("__does_not_exist__", "fr") == "__does_not_exist__"

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
    try:
        test_i18n()
        results.append(("i18n", True))
    except Exception as e:
        print(f"i18n test failed: {e}")
        results.append(("i18n", False))
    
    try:
        test_theme()
        results.append(("theme", True))
    except Exception as e:
        print(f"theme test failed: {e}")
        results.append(("theme", False))
    
    try:
        test_imports_in_modern_window()
        results.append(("modern_window", True))
    except Exception as e:
        print(f"modern_window test failed: {e}")
        results.append(("modern_window", False))
    
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
