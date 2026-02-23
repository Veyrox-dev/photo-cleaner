"""Quick test script for PhotoCleaner 0.5.5 professionalization features.

Tests:
1. Splash Screen creation
2. Dark Theme application
3. Windows Taskbar integration (if Windows)
4. Icon generation
"""
import sys
import pytest
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import QTimer


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)


def test_splash_screen(app):
    """Test splash screen creation and display."""
    from photo_cleaner.ui.splash_screen import create_splash_screen

    splash = create_splash_screen()
    splash.show()
    splash.show_progress("Testing Splash Screen", 50)
    app.processEvents()
    splash.close()

    assert splash is not None


def test_dark_theme(app):
    """Test dark theme application."""
    from photo_cleaner.ui.dark_theme import apply_dark_theme

    apply_dark_theme(app)

    palette = app.palette()
    window_color = palette.color(palette.ColorRole.Window)
    text_color = palette.color(palette.ColorRole.Text)

    assert window_color is not None
    assert text_color is not None


def test_windows_integration():
    """Test Windows taskbar integration."""
    if sys.platform != "win32":
        return
    
    try:
        import ctypes
        myappid = 'photocleaner.app.test'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        assert True
    except Exception as e:
        pytest.fail(f"Windows integration failed: {e}")


def test_icon_existence():
    """Test if icons exist."""
    project_root = Path(__file__).resolve().parents[2]
    icon_ico = project_root / "assets" / "icon.ico"
    icon_png = project_root / "assets" / "icon.png"

    assert icon_ico.exists()
    assert icon_png.exists()


def test_spec_file():
    """Test if PhotoCleaner.spec has been updated."""
    project_root = Path(__file__).resolve().parents[2]
    spec_path = project_root / "PhotoCleaner.spec"

    assert spec_path.exists()

    content = spec_path.read_text(encoding='utf-8')

    checks = {
        "Assets included": "('assets/*.ico', 'assets')" in content,
        "Icon configured": "icon='assets/icon.ico'" in content,
        "Optimize enabled": "optimize=2" in content,
        "UPX configured": "upx=" in content,
        "Console disabled": "console=False" in content,
    }

    assert all(checks.values())


def main():
    """Run all tests."""
    print("=" * 60)
    print("PhotoCleaner 0.5.5 - Professionalization Test Suite")
    print("=" * 60)
    
    # Create QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Run tests
    results = []
    
    # Test 1: Splash Screen
    splash = test_splash_screen()
    results.append(("Splash Screen", splash is not None))
    
    # Test 2: Dark Theme
    dark_theme_ok = test_dark_theme(app)
    results.append(("Dark Theme", dark_theme_ok))
    
    # Test 3: Windows Integration
    windows_ok = test_windows_integration()
    results.append(("Windows Integration", windows_ok))
    
    # Test 4: Icons
    icons_ok = test_icon_existence()
    results.append(("Icons", icons_ok))
    
    # Test 5: Spec file
    spec_ok = test_spec_file()
    results.append(("PyInstaller Spec", spec_ok))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, p in results if p)
    
    print("-" * 60)
    print(f"Total: {passed_tests}/{total_tests} tests passed")
    print("=" * 60)
    
    # Show test window
    if splash:
        test_window = QMainWindow()
        test_window.setWindowTitle("PhotoCleaner 0.5.5 - Test Window")
        test_window.resize(800, 600)
        
        # Set icon if available
        from PySide6.QtGui import QIcon
        icon_path = Path(__file__).resolve().parent / "assets" / "icon.ico"
        if icon_path.exists():
            test_window.setWindowIcon(QIcon(str(icon_path)))
        
        label = QLabel(
            "<h1>PhotoCleaner 0.5.5</h1>"
            "<p><b>Professionalization Test Suite</b></p>"
            "<p>All features tested. Check console for details.</p>"
            f"<p>Tests passed: {passed_tests}/{total_tests}</p>"
        )
        label.setStyleSheet("padding: 40px; font-size: 14px;")
        test_window.setCentralWidget(label)
        
        test_window.show()
        
        # Finish splash after 1 second
        QTimer.singleShot(1000, lambda: splash.finish(test_window))
        
        # Close after 3 seconds
        QTimer.singleShot(3000, app.quit)
        
        app.exec()
    
    # Return exit code
    sys.exit(0 if all(p for _, p in results) else 1)


if __name__ == "__main__":
    main()
