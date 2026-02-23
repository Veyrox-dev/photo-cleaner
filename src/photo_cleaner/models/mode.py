from __future__ import annotations

from enum import Enum


class AppMode(str, Enum):
    """Global operating mode controlling allowed actions."""

    REVIEW_MODE = "REVIEW_MODE"
    CLEANUP_MODE = "CLEANUP_MODE"
    SAFE_MODE = "SAFE_MODE"
