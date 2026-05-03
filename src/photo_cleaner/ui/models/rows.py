from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from photo_cleaner.models.status import FileStatus


@dataclass
class GroupRow:
    """Represents a duplicate group with metadata."""

    group_id: str
    sample_path: Path
    total: int
    open_count: int
    decided_count: int
    delete_count: int
    similarity: float
    needs_review_count: int = 0
    confidence_score: int = 0
    confidence_level: str = "none"
    diagnostics_text: str = ""


@dataclass
class FileRow:
    """Represents a file with its status and metadata."""

    path: Path
    status: FileStatus
    locked: bool
    is_recommended: bool
    quality_score: Optional[float] = None
    sharpness_score: Optional[float] = None
    lighting_score: Optional[float] = None
    resolution_score: Optional[float] = None
    face_quality_score: Optional[float] = None
