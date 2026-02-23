#!/usr/bin/env python3
"""Analyze hardcoded colors in PhotoCleaner UI and suggest replacements.

This script:
1. Finds all hardcoded hex colors and RGB values
2. Categorizes them (status, quality, semantic, component)
3. Suggests the appropriate constant from color_constants.py
4. Provides a migration guide

Usage:
    python scripts/analyze_colors.py
"""
import re
from pathlib import Path
from collections import defaultdict


# Color patterns
COLOR_HEX = r'#[0-9A-Fa-f]{6}'
COLOR_RGB = r'rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)'
COLOR_QCOLOR = r'QColor\((["\']?)([#\w0-9]+)\1\)'

# Known color mappings
COLOR_MAPPINGS = {
    "#4CAF50": {"name": "Green (Success/Keep)", "constant": "get_status_colors()['KEEP']"},
    "#F44336": {"name": "Red (Error/Delete)", "constant": "get_status_colors()['DELETE']"},
    "#FF9800": {"name": "Orange (Warning/Unsure)", "constant": "get_status_colors()['UNSURE']"},
    "#9E9E9E": {"name": "Gray (Neutral/Undecided)", "constant": "get_status_colors()['UNDECIDED']"},
    "#1976D2": {"name": "Dark Blue (High Quality)", "constant": "get_quality_colors()['high']"},
    "#42A5F5": {"name": "Medium Blue (Quality)", "constant": "get_quality_colors()['medium']"},
    "#64B5F6": {"name": "Light Blue (Low Quality)", "constant": "get_quality_colors()['low']"},
    "#2196F3": {"name": "Blue (Highlight/Link)", "constant": "get_semantic_colors()['info']"},
    "#FFEB3B": {"name": "Yellow (Warning)", "constant": "get_status_colors()['UNSURE']"},
    "#FF9900": {"name": "Orange (Bright Warning)", "constant": "get_status_colors()['UNSURE']"},
    "#E53935": {"name": "Red (Dark Error)", "constant": "get_status_colors()['DELETE']"},
    "#45a049": {"name": "Green (Dark Success)", "constant": "get_status_colors()['KEEP']"},
    "#1a1a1a": {"name": "Dark (Dark Theme Background)", "constant": "get_component_colors()['bg_main'] (dark)"},
    "#f5f5f5": {"name": "Light (Light Theme Background)", "constant": "get_component_colors()['bg_main'] (light)"},
    "#2a2a2a": {"name": "Dark Gray (Dark Theme Card)", "constant": "get_component_colors()['bg_card'] (dark)"},
    "#e0e0e0": {"name": "Light Gray (Light Theme Card)", "constant": "get_component_colors()['bg_card'] (light)"},
    "#BDBDBD": {"name": "Light Gray (Disabled)", "constant": "get_component_colors()['text_secondary']"},
    "#9C27B0": {"name": "Purple (Action)", "constant": "colors['highlight']"},
    "#7B1FA2": {"name": "Dark Purple (Action Dark)", "constant": "colors['highlight']"},
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def analyze_file(filepath: Path) -> dict:
    """Analyze a file for hardcoded colors."""
    result = {
        "file": str(filepath),
        "hex_colors": defaultdict(list),
        "rgb_colors": defaultdict(list),
        "total_colors": 0,
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        result["error"] = str(e)
        return result
    
    for line_num, line in enumerate(lines, 1):
        # Find hex colors
        for match in re.finditer(COLOR_HEX, line, re.IGNORECASE):
            color = match.group(0).upper()
            result["hex_colors"][color].append(line_num)
            result["total_colors"] += 1
        
        # Find RGB colors
        for match in re.finditer(COLOR_RGB, line):
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            color = f"rgb({r}, {g}, {b})"
            result["rgb_colors"][color].append(line_num)
            result["total_colors"] += 1
    
    return result


def main():
    """Analyze all UI files for hardcoded colors."""
    ui_dir = Path("src/photo_cleaner/ui")
    
    if not ui_dir.exists():
        print(f"Error: {ui_dir} not found")
        return
    
    print("=" * 80)
    print("PHOTOCLEANER COLOR HARDCODING ANALYSIS")
    print("=" * 80)
    print()
    
    all_colors = defaultdict(list)
    total_files = 0
    total_hardcoded = 0
    
    # Analyze all Python files in UI directory
    for py_file in sorted(ui_dir.rglob("*.py")):
        result = analyze_file(py_file)
        
        if result["total_colors"] == 0:
            continue
        
        total_files += 1
        total_hardcoded += result["total_colors"]
        
        print(f"\n[FILE] {py_file.name}")
        print(f"   Total hardcoded colors: {result['total_colors']}")
        
        # Hex colors
        if result["hex_colors"]:
            print("\n   HEX COLORS:")
            for color, lines in sorted(result["hex_colors"].items()):
                mapping = COLOR_MAPPINGS.get(color.upper())
                if mapping:
                    print(f"      {color:7s} - {mapping['name']:40s} (lines: {lines[:3]}...)")
                else:
                    print(f"      {color:7s} - UNKNOWN                              (lines: {lines[:3]}...)")
                
                all_colors[color.upper()].extend(lines)
        
        # RGB colors
        if result["rgb_colors"]:
            print("\n   RGB COLORS:")
            for color, lines in sorted(result["rgb_colors"].items()):
                print(f"      {color:30s} (lines: {lines[:3]}...)")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY")
    print("=" * 80)
    print(f"Files analyzed: {total_files}")
    print(f"Total hardcoded colors: {total_hardcoded}")
    
    print("\n" + "=" * 80)
    print("MIGRATION GUIDE")
    print("=" * 80)
    print("""
Instead of hardcoding colors, use the color_constants module:

    from photo_cleaner.ui.color_constants import (
        get_status_colors,
        get_quality_colors,
        get_semantic_colors,
        get_component_colors,
    )

STATUS COLORS (for file status badges):
    KEEP      = "#4CAF50"  ->  get_status_colors()['KEEP']
    DELETE    = "#F44336"  ->  get_status_colors()['DELETE']
    UNSURE    = "#FF9800"  ->  get_status_colors()['UNSURE']
    UNDECIDED = "#9E9E9E"  ->  get_status_colors()['UNDECIDED']

QUALITY COLORS (for quality score visualization):
    HIGH    = "#1976D2"  ->  get_quality_colors()['high']
    MEDIUM  = "#42A5F5"  ->  get_quality_colors()['medium']
    LOW     = "#64B5F6"  ->  get_quality_colors()['low']

SEMANTIC COLORS (for general meaning):
    SUCCESS = "#4CAF50"  ->  get_semantic_colors()['success']
    WARNING = "#FF9800"  ->  get_semantic_colors()['warning']
    ERROR   = "#F44336"  ->  get_semantic_colors()['error']
    INFO    = "#2196F3"  ->  get_semantic_colors()['info']

COMPONENT COLORS (theme-aware):
    Backgrounds    ->  get_component_colors()['bg_*']
    Borders        ->  get_component_colors()['border']
    Text           ->  get_component_colors()['text_*']

NEXT STEPS:
1. Create a refactoring task to gradually replace hardcoded colors
2. For immediate theme switching to work, colors in dynamic content
   (like status badges, quality scores) should use the color constants
3. StyleSheet-based colors are automatically handled by the theme system
4. For theme-aware inline colors, always get the color dynamically
    """)


if __name__ == "__main__":
    main()
