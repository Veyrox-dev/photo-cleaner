"""Theme management for PhotoCleaner (Dark/Light).

Complete theme system with StyleSheet generation and live switching support.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Literal

from PySide6.QtGui import QPalette, QColor

logger = logging.getLogger(__name__)

ThemeType = Literal["dark", "light"]

# Extended theme definitions with complete color palette
THEMES: Dict[ThemeType, Dict[str, str]] = {
    "dark": {
        # Main colors
        "window": "#1a1a1a",
        "window_text": "#ffffff",
        "base": "#0a0a0a",
        "alternate_base": "#2a2a2a",
        "text": "#ffffff",
        "button": "#2a2a2a",
        "button_text": "#ffffff",
        "highlight": "#2196F3",
        "highlighted_text": "#ffffff",
        "border": "#444444",
        "menu_bg": "#2a2a2a",
        
        # Additional widget colors
        "input_bg": "#0a0a0a",
        "input_text": "#ffffff",
        "input_border": "#404040",
        "tooltip_bg": "#2a82da",
        "tooltip_text": "#ffffff",
        "link": "#42b6f5",
        "link_visited": "#9e7bb5",
        "disabled_bg": "#1a1a1a",
        "disabled_text": "#7f7f7f",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#f44336",
        "scrollbar_bg": "#2b2b2b",
        "scrollbar_handle": "#555555",
        "scrollbar_handle_hover": "#666666",
    },
    "light": {
        # Main colors
        "window": "#f5f5f5",
        "window_text": "#000000",
        "base": "#ffffff",
        "alternate_base": "#ebebeb",
        "text": "#000000",
        "button": "#e0e0e0",
        "button_text": "#000000",
        "highlight": "#2196F3",
        "highlighted_text": "#ffffff",
        "border": "#cccccc",
        "menu_bg": "#f5f5f5",
        
        # Additional widget colors
        "input_bg": "#ffffff",
        "input_text": "#000000",
        "input_border": "#cccccc",
        "tooltip_bg": "#fffacd",
        "tooltip_text": "#000000",
        "link": "#0066cc",
        "link_visited": "#663399",
        "disabled_bg": "#f5f5f5",
        "disabled_text": "#999999",
        "success": "#2e7d32",
        "warning": "#f57c00",
        "error": "#c62828",
        "scrollbar_bg": "#f0f0f0",
        "scrollbar_handle": "#c0c0c0",
        "scrollbar_handle_hover": "#a0a0a0",
    },
}

# Current theme
_current_theme: ThemeType = "dark"


def set_theme(theme: ThemeType) -> None:
    """Set current theme (dark or light)."""
    global _current_theme
    if theme in THEMES:
        _current_theme = theme
        logger.info(f"Theme switched to: {theme}")
    else:
        logger.warning(f"Unknown theme: {theme}, using default (dark)")


def get_theme() -> ThemeType:
    """Get current theme."""
    return _current_theme


def get_theme_colors(theme: ThemeType | None = None) -> Dict[str, str]:
    """Get theme colors."""
    t = theme or _current_theme
    return THEMES.get(t, THEMES["dark"])


def apply_theme_to_palette(theme: ThemeType | None = None) -> QPalette:
    """Create and return a QPalette for the theme."""
    colors = get_theme_colors(theme)
    
    pal = QPalette()
    
    # Window and text colors (main UI)
    pal.setColor(QPalette.Window, QColor(colors["window"]))
    pal.setColor(QPalette.WindowText, QColor(colors["window_text"]))
    
    # Input/Edit widget colors
    pal.setColor(QPalette.Base, QColor(colors["base"]))
    pal.setColor(QPalette.AlternateBase, QColor(colors["alternate_base"]))
    pal.setColor(QPalette.Text, QColor(colors["text"]))
    
    # Button colors
    pal.setColor(QPalette.Button, QColor(colors["button"]))
    pal.setColor(QPalette.ButtonText, QColor(colors["button_text"]))
    
    # Highlight colors
    pal.setColor(QPalette.Highlight, QColor(colors["highlight"]))
    pal.setColor(QPalette.HighlightedText, QColor(colors["highlighted_text"]))
    
    # Disabled state colors
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor(colors["text"]))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(colors["button_text"]))
    
    # PlaceholderText and ToolTipBase
    pal.setColor(QPalette.PlaceholderText, QColor(colors["text"]))
    pal.setColor(QPalette.ToolTipBase, QColor(colors["button"]))
    pal.setColor(QPalette.ToolTipText, QColor(colors["button_text"]))
    
    return pal


def generate_stylesheet(theme: ThemeType | None = None) -> str:
    """Generate complete QSS stylesheet for the theme.
    
    Returns:
        Complete stylesheet string with all widget styling
    """
    colors = get_theme_colors(theme)
    
    stylesheet = f"""
    /* Main Window and Base Widgets */
    QMainWindow, QDialog, QWidget {{
        background-color: {colors['window']};
        color: {colors['window_text']};
    }}
    
    /* Text and Input */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {colors['input_bg']};
        color: {colors['input_text']};
        border: 1px solid {colors['input_border']};
        border-radius: 3px;
        padding: 5px;
    }}
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 2px solid {colors['highlight']};
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {colors['button']};
        color: {colors['button_text']};
        border: 1px solid {colors['input_border']};
        border-radius: 3px;
        padding: 5px 15px;
    }}
    
    QPushButton:hover {{
        background-color: {colors['alternate_base']};
    }}
    
    QPushButton:pressed {{
        background-color: {colors['alternate_base']};
    }}
    
    QPushButton:disabled {{
        color: {colors['disabled_text']};
        background-color: {colors['alternate_base']};
    }}

    /* Dialog Buttons (Primary look) */
    QDialog QPushButton {{
        background-color: {colors['highlight']};
        color: {colors['highlighted_text']};
        border: 1px solid {colors['highlight']};
        border-radius: 6px;
        padding: 7px 14px;
        font-weight: 600;
    }}

    QDialog QPushButton:hover {{
        background-color: {colors['link']};
    }}

    QDialog QPushButton:disabled {{
        background-color: {colors['disabled_bg']};
        color: {colors['disabled_text']};
        border: 1px solid {colors['border']};
        font-weight: normal;
    }}
    
    /* Tooltips */
    QToolTip {{
        background-color: {colors['tooltip_bg']};
        color: {colors['tooltip_text']};
        border: 1px solid {colors['border']};
        padding: 5px;
        border-radius: 3px;
    }}
    
    /* ScrollBars */
    QScrollBar:vertical {{
        background: {colors['scrollbar_bg']};
        width: 12px;
        margin: 0px;
    }}
    
    QScrollBar::handle:vertical {{
        background: {colors['scrollbar_handle']};
        min-height: 20px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: {colors['scrollbar_handle_hover']};
    }}
    
    QScrollBar:horizontal {{
        background: {colors['scrollbar_bg']};
        height: 12px;
        margin: 0px;
    }}
    
    QScrollBar::handle:horizontal {{
        background: {colors['scrollbar_handle']};
        min-width: 20px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background: {colors['scrollbar_handle_hover']};
    }}
    
    /* ComboBox */
    QComboBox {{
        background-color: {colors['button']};
        color: {colors['button_text']};
        border: 1px solid {colors['input_border']};
        border-radius: 3px;
        padding: 5px;
    }}
    
    QComboBox:hover {{
        border: 1px solid {colors['highlight']};
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {colors['button']};
        color: {colors['button_text']};
        selection-background-color: {colors['highlight']};
    }}
    
    /* Menu */
    QMenu {{
        background-color: {colors['menu_bg']};
        color: {colors['window_text']};
        border: 1px solid {colors['border']};
    }}
    
    QMenu::item:selected {{
        background-color: {colors['highlight']};
    }}
    
    /* Groups and Frames */
    QGroupBox, QFrame {{
        border: 1px solid {colors['border']};
        border-radius: 3px;
        color: {colors['window_text']};
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 3px;
    }}
    
    /* Tabs */
    QTabBar::tab {{
        background-color: {colors['button']};
        color: {colors['button_text']};
        padding: 5px 15px;
        border: 1px solid {colors['border']};
    }}
    
    QTabBar::tab:selected {{
        background-color: {colors['highlight']};
        color: {colors['highlighted_text']};
    }}
    
    /* Sliders */
    QSlider::groove:horizontal {{
        border: 1px solid {colors['input_border']};
        background: {colors['alternate_base']};
        height: 8px;
        margin: 2px 0;
        border-radius: 4px;
    }}
    
    QSlider::handle:horizontal {{
        background: {colors['button']};
        border: 1px solid {colors['border']};
        width: 18px;
        margin: -5px 0;
        border-radius: 9px;
    }}
    
    /* CheckBox and RadioButton */
    QCheckBox, QRadioButton {{
        color: {colors['window_text']};
        spacing: 5px;
    }}
    
    /* SpinBox */
    QSpinBox, QDoubleSpinBox {{
        background-color: {colors['input_bg']};
        color: {colors['input_text']};
        border: 1px solid {colors['input_border']};
        border-radius: 3px;
        padding: 5px;
    }}
    
    /* ProgressBar */
    QProgressBar {{
        background-color: {colors['alternate_base']};
        border: 1px solid {colors['border']};
        border-radius: 3px;
        color: {colors['window_text']};
    }}
    
    QProgressBar::chunk {{
        background-color: {colors['success']};
        border-radius: 2px;
    }}
    
    /* StatusBar */
    QStatusBar {{
        color: {colors['window_text']};
        background-color: {colors['button']};
    }}
    
    /* TreeView and ListView */
    QTreeView, QListView {{
        background-color: {colors['base']};
        color: {colors['text']};
        border: 1px solid {colors['border']};
        selection-background-color: {colors['highlight']};
    }}
    
    QHeaderView::section {{
        background-color: {colors['button']};
        color: {colors['button_text']};
        padding: 5px;
        border: 1px solid {colors['border']};
    }}
    """
    
    return stylesheet


def load_theme_from_settings(settings_path: Path) -> ThemeType:
    """Load theme preference from settings file.
    
    Returns:
        Theme (dark or light), or "dark" if not found
    """
    try:
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                theme = data.get("theme", "dark")
                if theme in THEMES:
                    set_theme(theme)  # type: ignore
                    return theme  # type: ignore
    except Exception as e:
        logger.warning(f"Could not load theme from settings: {e}")
    
    return "dark"


def save_theme_to_settings(settings_path: Path, theme: ThemeType) -> bool:
    """Save theme preference to settings file.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read existing settings
        data = {}
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # Update theme
        data["theme"] = theme
        
        # Write back
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Could not save theme to settings: {e}")
        return False
