from __future__ import annotations

from enum import Enum


class FileStatus(str, Enum):
    """Persistent status of a file used across UI and services."""

    UNDECIDED = "UNDECIDED"
    KEEP = "KEEP"
    DELETE = "DELETE"
    UNSURE = "UNSURE"
    LOCKED = "LOCKED"
