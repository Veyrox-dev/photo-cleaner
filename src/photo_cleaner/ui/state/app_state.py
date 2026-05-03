from __future__ import annotations

from dataclasses import dataclass, field

from photo_cleaner.ui.models.rows import FileRow, GroupRow


@dataclass
class AppState:
    """Central UI state container for the main window."""

    groups: list[GroupRow] = field(default_factory=list)
    group_lookup: dict[str, GroupRow] = field(default_factory=dict)
    files_in_group: list[FileRow] = field(default_factory=list)
    current_group: str | None = None
    current_page: int = 0
    checked_group_ids: set[str] = field(default_factory=set)
    group_selection_state: dict[str, tuple[set[int], int]] = field(default_factory=dict)
