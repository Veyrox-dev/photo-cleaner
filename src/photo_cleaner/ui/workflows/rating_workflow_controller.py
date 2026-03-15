from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QProgressDialog, QWidget


class RatingWorkflowController:
    """Controller for creating and starting the rating workflow thread."""

    def __init__(
        self,
        owner: QWidget,
        rating_thread_factory,
        process_events: Callable[[], None],
    ) -> None:
        self._owner = owner
        self._rating_thread_factory = rating_thread_factory
        self._process_events = process_events

    def create_and_wire_rating_thread(
        self,
        db_path: Path,
        top_n: int,
        mtcnn_status: dict | None,
        *,
        on_progress,
        on_finished,
        on_error,
    ):
        """Create rating worker thread and connect all callbacks."""
        thread = self._rating_thread_factory(db_path, top_n, mtcnn_status)
        thread.progress.connect(on_progress)
        thread.finished.connect(on_finished)
        thread.error.connect(on_error)
        return thread

    def start_rating_thread(self, thread, progress_dialog: QProgressDialog | None) -> None:
        """Start thread and ensure progress dialog updates are shown immediately."""
        thread.start()

        if progress_dialog and not progress_dialog.isVisible():
            progress_dialog.show()

        self._process_events()
