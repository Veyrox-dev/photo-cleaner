# PhotoCleaner Theme System

## Overview

Das PhotoCleaner Theme-System bietet Live-Theme-Wechsel ohne Neustart. Der Nutzer kann zwischen "Dark" und "Light" Mode wechseln, und die gesamte UI wird sofort aktualisiert.

## Architecture

### Core Components

1. **theme.py** - Theme-Verwaltung
   - Definiert alle Theme-Farben
   - Generiert QPalette aus Theme-Farben
   - Generiert komplette QSS-StyleSheets
   - Persistiert Theme-Einstellungen

2. **theme_manager.py** - Zentraler Theme-Manager (Singleton)
   - `ThemeManager.instance()` - Abrufen des Singletons
   - `change_theme(theme, main_window)` - Theme ändern mit Live-Update
   - Emittiert `theme_changed` Signal für alle Listener
   - Updatet alle Widgets rekursiv

3. **color_constants.py** - Zentrale Farbkonstanten
   - `get_status_colors()` - Status-Farben (Keep, Delete, Unsure, Undecided)
   - `get_quality_colors()` - Qualitäts-Farben (High, Medium, Low)
   - `get_semantic_colors()` - Semantische Farben (Success, Warning, Error, Info)
   - `get_component_colors()` - Komponenten-Farben (Theme-aware)

## Color Definitions

### Dark Theme
```
Window:          #1a1a1a
Text:            #ffffff
Base:            #0a0a0a
Button:          #2a2a2a
Highlight:       #2196F3
Border:          #444444
Input:           #0a0a0a
```

### Light Theme
```
Window:          #f5f5f5
Text:            #000000
Base:            #ffffff
Button:          #e0e0e0
Highlight:       #2196F3
Border:          #cccccc
Input:           #ffffff
```

## Usage Examples

### Changing Theme Programmatically

```python
from photo_cleaner.ui.theme_manager import ThemeManager

# Get singleton instance
manager = ThemeManager.instance()

# Change theme (will update entire UI)
manager.change_theme("light", main_window=self)

# Listen to theme changes
manager.theme_changed.connect(self.on_theme_changed)
```

### Using Color Constants

```python
from photo_cleaner.ui.color_constants import (
    get_status_colors,
    get_quality_colors,
    get_semantic_colors,
)

# Status colors (for file status badges)
colors = get_status_colors()
keep_color = colors['KEEP']      # #4CAF50 (green)
delete_color = colors['DELETE']  # #F44336 (red)

# Quality colors (for quality score visualization)
quality = get_quality_colors()
high_quality = quality['high']    # #1976D2

# Semantic colors (for general meaning)
semantic = get_semantic_colors()
success = semantic['success']     # #4CAF50
```

### Using Theme-Aware StyleSheets

```python
from photo_cleaner.theme import generate_stylesheet

# Apply complete stylesheet to QApplication
stylesheet = generate_stylesheet()
QApplication.instance().setStyleSheet(stylesheet)
```

## How Live Switching Works

1. **User selects new theme** from menu
   - Calls: `_change_theme(theme_name)`

2. **ThemeManager updates global state**
   - Updates theme in `theme.py` global variable
   - Saves to settings file
   
3. **Palette is regenerated**
   - Creates new QPalette with theme colors
   - Applies to QApplication and all widgets

4. **StyleSheet is regenerated**
   - Generates complete QSS with theme colors
   - Applies to QApplication

5. **Widget tree is updated**
   - Recursively updates all child widgets
   - Forces repaint/update on all widgets

6. **Signal is emitted**
   - `theme_changed` signal emitted
   - Other components can react if needed

## Key Features

### ✅ Live Switching
- No application restart required
- All widgets update immediately
- Smooth visual transition

### ✅ Persistence
- Theme choice saved to `~/.photocleaner/settings.json`
- Restored on next app start

### ✅ Complete Coverage
- QPalette colors
- QSS StyleSheets
- ScrollBars, ComboBox, Menu, etc.
- All widget types

### ✅ Dynamic Colors
- Status colors change with theme
- Quality score colors adapt
- Input backgrounds are always visible

## Migration Guide

To remove hardcoded colors from your code:

### Before (Hardcoded)
```python
self.label.setStyleSheet("color: #4CAF50; font-weight: bold;")
```

### After (Dynamic)
```python
from photo_cleaner.ui.color_constants import get_status_colors

colors = get_status_colors()
self.label.setStyleSheet(f"color: {colors['KEEP']}; font-weight: bold;")
```

### Or use ThemeManager for palette-based coloring
```python
from photo_cleaner.ui.theme_manager import ThemeManager

manager = ThemeManager.instance()
theme_colors = manager.get_theme_colors()
```

## Analyzing Hardcoded Colors

To find and analyze all hardcoded colors in the codebase:

```bash
python scripts/analyze_colors.py
```

This script:
- Scans all UI files for hex colors and RGB values
- Categorizes them (status, quality, semantic, component)
- Suggests the appropriate replacement
- Generates a migration guide

## Best Practices

1. **Use color_constants module** for all UI colors
2. **Use ThemeManager** for theme-aware operations
3. **Use StyleSheets** instead of hardcoded palette colors
4. **Test in both themes** when making UI changes
5. **Avoid hardcoding colors** - always reference the theme

## Testing Theme Changes

1. Open PhotoCleaner
2. Click Menü → Theme → Light (or Dark)
3. Verify all UI elements immediately update
4. Check no refresh/restart needed
5. Close and reopen app
6. Verify theme persists from previous session

## Troubleshooting

### Theme not persisting
- Check `~/.photocleaner/settings.json` is writable
- Check no exceptions in `theme.py` save_theme_to_settings()

### Some widgets not updating
- Ensure widget is in the main window's widget tree
- Call `manager.apply_to_widget(widget)` for custom widgets
- Check no hardcoded colors in QSS stylesheets

### Colors look wrong in Light theme
- Check `color_constants.py` is being used
- Don't hardcode dark theme colors
- Use `get_theme_colors()` for dynamic colors

## Files Modified

- `src/photo_cleaner/theme.py` - Enhanced with StyleSheet generation
- `src/photo_cleaner/ui/theme_manager.py` - NEW - Central theme management
- `src/photo_cleaner/ui/color_constants.py` - NEW - Color constants
- `src/photo_cleaner/ui/modern_window.py` - Uses ThemeManager for live switching
- `scripts/analyze_colors.py` - NEW - Color analysis tool

## Future Improvements

- [ ] System theme detection (Windows dark/light preference)
- [ ] Custom theme creator
- [ ] Per-widget theme overrides
- [ ] Theme animations
- [ ] Save custom theme colors
- [ ] Theme scheduler (auto-switch based on time of day)
