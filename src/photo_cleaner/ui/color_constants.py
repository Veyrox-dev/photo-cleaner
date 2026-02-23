"""Color constants for PhotoCleaner UI.

All hardcoded colors are centralized here and reference the theme system.
Use these constants instead of hardcoding color hex values.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from photo_cleaner.theme import ThemeType


def get_status_colors() -> dict[str, str]:
    """Get status-specific colors (theme-aware).
    
    Returns:
        Mapping of status -> color
    """
    from photo_cleaner.theme import get_theme_colors
    
    return {
        "KEEP": "#4CAF50",      # Green - action to keep
        "DELETE": "#F44336",    # Red - action to delete
        "UNSURE": "#FF9800",    # Orange - user is unsure
        "UNDECIDED": "#9E9E9E", # Gray - not decided yet
        "UNDECIDED_ATTENTION": "#FF9900", # Bright orange for attention states
    }


def get_quality_colors() -> dict[str, str]:
    """Get quality score colors (gradient from low to high).
    
    Returns:
        Mapping: high -> dark blue, medium -> medium blue, low -> light blue
    """
    return {
        "high": "#1976D2",    # Dark Blue (high quality)
        "medium": "#42A5F5",  # Medium Blue (medium quality)
        "low": "#64B5F6",     # Light Blue (low quality)
    }


def get_semantic_colors() -> dict[str, str]:
    """Get semantic meaning colors.
    
    Returns:
        Mapping of semantic meaning -> color
    """
    return {
        "success": "#4CAF50",      # Green - success
        "warning": "#FF9800",      # Orange - warning
        "error": "#F44336",        # Red - error
        "info": "#2196F3",         # Blue - information
        "neutral": "#9E9E9E",      # Gray - neutral/disabled
        "link": "#2196F3",         # Blue - link
    }


def get_component_colors(theme: ThemeType | None = None) -> dict[str, str]:
    """Get colors for specific UI components (background, borders, etc).
    
    Args:
        theme: The theme to get colors for. If None, uses current theme.
    
    Returns:
        Mapping of component -> color
    """
    from photo_cleaner.theme import get_theme_colors
    
    colors = get_theme_colors(theme)
    
    return {
        "bg_main": colors["window"],
        "bg_card": colors["button"],
        "bg_input": colors["input_bg"],
        "bg_alternate": colors["alternate_base"],
        "border": colors["border"],
        "text_primary": colors["text"],
        "text_secondary": colors["disabled_text"],
        "text_hint": colors["disabled_text"],
        "highlight": colors["highlight"],
        "success": colors["success"],
        "warning": colors["warning"],
        "error": colors["error"],
    }


def get_text_hint_color(theme: ThemeType | None = None) -> str:
    """Get the hint/description text color for current theme.
    
    Returns:
        Hex color string for hint text
    """
    from photo_cleaner.theme import get_theme
    t = theme or get_theme()
    return "#888888" if t == "dark" else "#666666"


def get_label_background_color(theme: ThemeType | None = None) -> str:
    """Get background color for labels/display areas.
    
    Returns:
        Hex color string for label backgrounds
    """
    from photo_cleaner.theme import get_theme
    t = theme or get_theme()
    return "#2a2a2a" if t == "dark" else "#f0f0f0"


def get_label_foreground_color(theme: ThemeType | None = None) -> str:
    """Get foreground/text color for labels.
    
    Returns:
        Hex color string for label text
    """
    from photo_cleaner.theme import get_theme
    t = theme or get_theme()
    return "#888888" if t == "dark" else "#666666"


def get_card_colors(theme: ThemeType | None = None) -> dict[str, str]:
    """Get colors for card-style widgets (thumbnail cards, etc).
    
    Returns:
        Mapping with bg, bg_hover, border
    """
    from photo_cleaner.theme import get_theme
    t = theme or get_theme()
    
    if t == "dark":
        return {
            "bg": "#2a2a2a",
            "bg_hover": "#333333",
            "bg_selected": "#1f5a57",
            "border": "#444444",
        }
    else:
        return {
            "bg": "#f5f5f5",
            "bg_hover": "#e8e8e8",
            "bg_selected": "#cfeee8",
            "border": "#cccccc",
        }


def get_high_contrast_colors() -> dict[str, str]:
    """Get fixed colors for the high-contrast palette."""
    return {
        "window": "#000000",
        "window_text": "#FFFF00",
        "base": "#000000",
        "alternate_base": "#2a2a2a",
        "text": "#FFFF00",
        "button": "#000000",
        "button_text": "#FFFF00",
        "highlight": "#00FFFF",
        "highlighted_text": "#000000",
    }


def to_rgba(color_hex: str, alpha: float) -> str:
    """Convert hex color to an rgba() CSS string.

    Args:
        color_hex: Hex string like "#RRGGBB".
        alpha: 0.0-1.0 alpha value.
    """
    color_hex = color_hex.lstrip("#")
    r = int(color_hex[0:2], 16)
    g = int(color_hex[2:4], 16)
    b = int(color_hex[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
