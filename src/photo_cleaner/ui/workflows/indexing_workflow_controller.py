from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QProgressDialog, QWidget

from photo_cleaner.i18n import t
from photo_cleaner.ui.indexing_thread import IndexingThread


class IndexingWorkflowController:
    """Controller for indexing and post-indexing dialog/thread setup."""

    def __init__(
        self,
        owner: QWidget,
        center_dialog_text: Callable[[QProgressDialog], None],
    ) -> None:
        self._owner = owner
        self._center_dialog_text = center_dialog_text

    def build_indexer(self, db_path: Path):
        """Build a thread-local indexer with its own DB connection."""
        from photo_cleaner.core.indexer import PhotoIndexer
        from photo_cleaner.db.schema import Database

        indexer_db = Database(db_path)
        indexer_db.connect()
        return PhotoIndexer(indexer_db, max_workers=None)

    def create_indexing_progress_dialog(self) -> QProgressDialog:
        """Create the modal progress dialog for folder indexing."""
        dialog = QProgressDialog(
            "Bilder werden analysiert...",
            "Abbrechen",
            0,
            100,
            self._owner,
        )
        dialog.setWindowTitle(t("image_analysis_async"))
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)
        dialog.setMinimumWidth(460)
        dialog.setMinimumHeight(140)
        dialog.setStyleSheet(
            "QLabel { padding: 6px 8px; }"
            "QProgressBar { min-height: 18px; text-align: center; }"
        )
        self._center_dialog_text(dialog)
        return dialog

    def create_indexing_thread(
        self,
        input_folder: Path,
        indexer,
        *,
        on_progress,
        on_finished,
        on_error,
    ) -> IndexingThread:
        """Create and wire the indexing thread callbacks."""
        thread = IndexingThread(input_folder, indexer, use_incremental=True)
        thread.progress.connect(on_progress)
        thread.finished.connect(on_finished)
        thread.error.connect(on_error)
        return thread

    def create_post_indexing_progress_dialog(
        self,
        *,
        on_cancel,
    ) -> QProgressDialog:
        """Create the modal progress dialog for duplicate/rating stage."""
        dialog = QProgressDialog(
            "Duplikate werden gesucht...",
            t("cancel"),
            0,
            0,
            self._owner,
        )
        dialog.setWindowTitle(t("image_analysis"))
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)
        dialog.setMinimumWidth(460)
        dialog.setMinimumHeight(140)
        dialog.setStyleSheet(
            "QLabel { padding: 6px 8px; }"
            "QProgressBar { min-height: 18px; text-align: center; }"
        )
        self._center_dialog_text(dialog)
        dialog.canceled.connect(on_cancel)
        return dialog
