from __future__ import annotations

from pathlib import Path

from photo_cleaner.models.mode import AppMode
from photo_cleaner.models.status import FileStatus
from photo_cleaner.repositories.file_repository import FileRepository
from photo_cleaner.repositories.history_repository import HistoryRepository


class StatusService:
    """Business rules for status changes, locking, and undo."""

    def __init__(self, files: FileRepository, history: HistoryRepository, mode_getter, is_exact_duplicate=None) -> None:
        """Service-layer guards; UI is not trusted.

        LOCK does not change status automatically; status remains until explicitly set.
        """
        self.files = files
        self.history = history
        self.mode_getter = mode_getter  # callable returning AppMode
        self.is_exact_duplicate = is_exact_duplicate or (lambda _p: False)

    def set_status(
        self,
        path: Path,
        status: FileStatus,
        *,
        reason: str = "",
        allow_delete_in_safe: bool = True,
        action_id: str = "MANUAL_SET",
    ) -> None:
        mode = self.mode_getter()
        current_status, is_locked = self.files.get_status(path)
        if is_locked:
            raise PermissionError("File is locked")
        if mode == AppMode.REVIEW_MODE and status == FileStatus.DELETE:
            raise PermissionError("Delete not allowed in REVIEW_MODE")
        if mode == AppMode.SAFE_MODE and status == FileStatus.DELETE and not allow_delete_in_safe:
            if not self.is_exact_duplicate(path):
                raise PermissionError("Delete blocked in SAFE_MODE (not exact duplicate)")
        self.files.set_status(path, status, reason=reason, action_id=action_id)

    def toggle_lock(self, path: Path, *, lock: bool | None = None, reason: str = "", action_id: str = "LOCK_TOGGLE") -> bool:
        _current_status, _is_locked = self.files.get_status(path)
        return self.files.toggle_lock(path, lock=lock, reason=reason, action_id=action_id)

    def undo_last(self) -> bool:
        return self.history.undo_last_action()
