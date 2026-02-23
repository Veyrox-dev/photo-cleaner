"""Theme Manager with live theme switching support.

Handles theme changes across the entire application with immediate visual updates.
All child widgets are updated when theme changes without requiring app restart.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QAbstractItemView

from photo_cleaner.theme import (
    ThemeType,
    set_theme,
    get_theme,
    apply_theme_to_palette,
    generate_stylesheet,
    save_theme_to_settings,
    get_theme_colors,
)
from photo_cleaner.config import AppConfig

logger = logging.getLogger(__name__)


class ThemeManager(QObject):
    """Central theme manager with live switching support.
    
    Emits signals when theme changes so all widgets can update immediately.
    """
    
    # Signal emitted when theme changes (str is the new theme name)
    theme_changed = Signal(str)
    
    _instance: Optional[ThemeManager] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the theme manager."""
        if self._initialized:
            return
        
        super().__init__()
        self._initialized = True
        self.current_theme = get_theme()
        logger.info(f"ThemeManager initialized with theme: {self.current_theme}")
    
    @classmethod
    def instance(cls) -> ThemeManager:
        """Get the singleton instance."""
        return cls()
    
    def change_theme(self, theme: ThemeType, main_window: Optional[QMainWindow] = None) -> None:
        """Change the application theme and update all widgets.
        
        Args:
            theme: The theme to switch to ("dark" or "light")
            main_window: Optional main window to update (and all its children)
        """
        try:
            # Update global theme state
            set_theme(theme)
            self.current_theme = theme
            
            # Persist to settings
            save_theme_to_settings(AppConfig.get_user_data_dir() / "settings.json", theme)
            
            # Update QApplication palette
            app = QApplication.instance()
            if app:
                palette = apply_theme_to_palette()
                app.setPalette(palette)
                
                # Update stylesheet
                stylesheet = generate_stylesheet()
                app.setStyleSheet(stylesheet)
                
                # Update main window and all children
                if main_window:
                    self._update_widget_tree(main_window)
                else:
                    # Update all top-level widgets
                    for widget in app.topLevelWidgets():
                        self._update_widget_tree(widget)
            
            # Emit signal so other components can react
            self.theme_changed.emit(theme)
            logger.info(f"Theme changed to: {theme}")
            
        except (RuntimeError, AttributeError, TypeError) as e:
            logger.error(f"Error changing theme: {e}", exc_info=True)
    
    def _update_widget_tree(self, widget: QWidget) -> None:
        """Recursively update palette and stylesheet for widget and all children.
        
        Args:
            widget: The root widget to update
        """
        try:
            palette = apply_theme_to_palette()
            widget.setPalette(palette)
            
            # Update all child widgets
            for child in widget.findChildren(QWidget):
                child.setPalette(palette)
                # Force repaint (QAbstractItemView.update expects an index)
                if isinstance(child, QAbstractItemView):
                    child.viewport().update()
                else:
                    child.update()
                child.repaint()
            
            # Force full repaint
            if isinstance(widget, QAbstractItemView):
                widget.viewport().update()
            else:
                widget.update()
            widget.repaint()
            
        except (RuntimeError, AttributeError, TypeError) as e:
            logger.error(f"Error updating widget tree: {e}")
    
    def get_current_theme(self) -> ThemeType:
        """Get the current theme."""
        return self.current_theme
    
    def get_theme_colors(self) -> dict[str, str]:
        """Get the color palette for the current theme."""
        return get_theme_colors()
    
    def apply_to_widget(self, widget: QWidget) -> None:
        """Apply the current theme to a specific widget and its children.
        
        Args:
            widget: The widget to apply theme to
        """
        palette = apply_theme_to_palette()
        widget.setPalette(palette)
        
        for child in widget.findChildren(QWidget):
            child.setPalette(palette)
