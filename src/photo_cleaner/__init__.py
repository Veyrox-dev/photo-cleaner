# src/photo_cleaner/__init__.py
"""Photo Cleaner - Local photo collection analyzer and duplicate detector."""

__version__ = "0.8.7"  # Export options + UI consistency update

# Import config to make it available at package level
from photo_cleaner.config import AppConfig, AppMode, get_logger, is_debug, is_release

__all__ = ["AppConfig", "AppMode", "get_logger", "is_debug", "is_release"]

# src/photo_cleaner/core/__init__.py
"""Core business logic modules."""

# src/photo_cleaner/ml/__init__.py
"""Image processing and computer vision modules."""

# src/photo_cleaner/io/__init__.py
"""Input/output utilities."""

# src/photo_cleaner/db/__init__.py
"""Database layer."""

# src/photo_cleaner/ui/__init__.py
"""GUI components (PySide6)."""