"""Dark Theme für PhotoCleaner.

Erzwingt ein konsistentes Dark Theme unabhängig vom Windows-Theme.
Verhindert das Problem mit weißer Schrift auf weißem Hintergrund.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_dark_theme(app: QApplication):
    """Erzwinge konsistentes Dark Theme unabhängig von Windows.
    
    Setzt:
    - Fusion Style (bessere Dark Mode Unterstützung)
    - Dunkle QPalette für alle Widgets
    - Custom StyleSheet für spezielle Widgets
    
    Args:
        app: QApplication-Instanz
    """
    # 1. Fusion Style (bessere Dark Mode Unterstützung als Windows-Style)
    app.setStyle("Fusion")
    
    # 2. Erstelle dunkle Palette
    dark_palette = QPalette()
    
    # Base Colors - Hauptfarben
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    
    # Button Colors
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    
    # Link & Highlight Colors
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    
    # Disabled State - Ausgegraut
    dark_palette.setColor(
        QPalette.ColorGroup.Disabled, 
        QPalette.ColorRole.Text, 
        QColor(127, 127, 127)
    )
    dark_palette.setColor(
        QPalette.ColorGroup.Disabled, 
        QPalette.ColorRole.ButtonText, 
        QColor(127, 127, 127)
    )
    dark_palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(127, 127, 127)
    )
    
    # 3. Setze Palette
    app.setPalette(dark_palette)
    
    # 4. Custom StyleSheet für spezielle Widgets
    app.setStyleSheet("""
        /* Tooltips */
        QToolTip {
            color: #ffffff;
            background-color: #2a82da;
            border: 1px solid white;
            padding: 5px;
            border-radius: 3px;
        }
        
        /* Progress Bars */
        QProgressBar {
            border: 2px solid #404040;
            border-radius: 5px;
            text-align: center;
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QProgressBar::chunk {
            background-color: #2a82da;
            border-radius: 3px;
        }
        
        /* Scroll Bars */
        QScrollBar:vertical {
            border: none;
            background: #2b2b2b;
            width: 12px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #666666;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            border: none;
            background: #2b2b2b;
            height: 12px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #555555;
            min-width: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #666666;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        /* ComboBox */
        QComboBox {
            border: 1px solid #404040;
            border-radius: 3px;
            padding: 5px;
            background-color: #353535;
            color: #ffffff;
        }
        QComboBox:hover {
            border: 1px solid #2a82da;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #353535;
            color: #ffffff;
            selection-background-color: #2a82da;
        }
        
        /* Line Edit */
        QLineEdit {
            border: 1px solid #404040;
            border-radius: 3px;
            padding: 5px;
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QLineEdit:focus {
            border: 1px solid #2a82da;
        }
        
        /* Spin Box */
        QSpinBox, QDoubleSpinBox {
            border: 1px solid #404040;
            border-radius: 3px;
            padding: 5px;
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QSpinBox:focus, QDoubleSpinBox:focus {
            border: 1px solid #2a82da;
        }
        
        /* Group Box */
        QGroupBox {
            border: 2px solid #404040;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
        }
        
        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #404040;
            background-color: #353535;
        }
        QTabBar::tab {
            background-color: #2b2b2b;
            color: #ffffff;
            padding: 8px 12px;
            border: 1px solid #404040;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #353535;
            border-bottom: 2px solid #2a82da;
        }
        QTabBar::tab:hover:!selected {
            background-color: #404040;
        }
        
        /* Sliders */
        QSlider::groove:horizontal {
            border: 1px solid #404040;
            height: 8px;
            background: #2b2b2b;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #2a82da;
            border: 1px solid #1a5f9a;
            width: 18px;
            margin: -5px 0;
            border-radius: 9px;
        }
        QSlider::handle:horizontal:hover {
            background: #3a92da;
        }
        
        /* Check Box */
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #404040;
            border-radius: 3px;
            background-color: #2b2b2b;
        }
        QCheckBox::indicator:checked {
            background-color: #2a82da;
            border-color: #2a82da;
        }
        QCheckBox::indicator:hover {
            border-color: #2a82da;
        }
        
        /* Radio Button */
        QRadioButton::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #404040;
            border-radius: 9px;
            background-color: #2b2b2b;
        }
        QRadioButton::indicator:checked {
            background-color: #2a82da;
            border-color: #2a82da;
        }
        QRadioButton::indicator:hover {
            border-color: #2a82da;
        }
    """)


def apply_light_theme(app: QApplication):
    """Alternative: Light Theme (für zukünftige Umschaltmöglichkeit).
    
    Args:
        app: QApplication-Instanz
    """
    # Zurück zum System-Standard
    app.setStyle("Fusion")
    app.setPalette(app.style().standardPalette())
    app.setStyleSheet("")  # Entferne custom styles
