"""
Async indexing worker for non-blocking image processing.

Runs indexing in a dedicated Qt thread to keep UI responsive
during large photo scans (100k+ images).

v0.5.3 Feature: IndexingThread with progress signals
"""

import logging
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QThread, Signal

from photo_cleaner.core.indexer import PhotoIndexer
from photo_cleaner.db.schema import Database

logger = logging.getLogger(__name__)


class IndexingThread(QThread):
    """
    Worker thread for image indexing.
    
    Runs indexing in background without blocking UI.
    Emits signals for progress updates, status messages, errors.
    
    Usage:
        thread = IndexingThread(folder_path, indexer)
        thread.progress.connect(on_progress)
        thread.finished.connect(on_finished)
        thread.error.connect(on_error)
        thread.start()
    """
    
    # Signals
    progress = Signal(int, int, str)  # (current, total, status_message)
    status = Signal(str)  # status_message
    finished = Signal(dict)  # results dict
    error = Signal(str)  # error message
    
    def __init__(
        self,
        folder_path: Path,
        indexer: PhotoIndexer,
        use_incremental: bool = True,
    ):
        """
        Initialize indexing worker thread.
        
        Args:
            folder_path: Root folder to index
            indexer: PhotoIndexer instance
            use_incremental: Use incremental scanning if True
        """
        super().__init__()
        self.folder_path = folder_path
        self.indexer = indexer
        self.use_incremental = use_incremental
        self._should_stop = False
        
        logger.info(
            f"IndexingThread initialized: folder={folder_path}, "
            f"incremental={use_incremental}"
        )
    
    def run(self):
        """
        Run indexing in background thread.
        
        Called when thread.start() is invoked.
        Emits progress/finished/error signals to UI thread.
        """
        logger.info("=== IndexingThread.run() STARTED ===")
        logger.info(f"Folder: {self.folder_path}")
        logger.info(f"Use incremental: {self.use_incremental}")
        try:
            self.status.emit("Starting indexing...")
            
            # Define progress callback
            def progress_callback(current, total, status_msg):
                if not self._should_stop:
                    self.progress.emit(current, total, status_msg)
                    logger.debug(f"Progress: {current}/{total} - {status_msg}")
            
            # Run indexing
            if self.use_incremental:
                logger.info("Using incremental indexing")
                results = self.indexer.index_folder_incremental(
                    self.folder_path,
                    progress_callback=progress_callback,
                )
            else:
                logger.info("Using full indexing")
                results = self.indexer.index_folder(
                    self.folder_path,
                    skip_existing=False,
                )
                # Convert to incremental result format
                results = {
                    "total_files": results.get("processed", 0),
                    "new_files": results.get("processed", 0),
                    "hashed_files": results.get("processed", 0),
                    "cached_files": 0,
                    "duplicates_found": 0,
                    "speedup_factor": 1.0,
                }
            
            self.status.emit("Indexing complete!")
            logger.info("=== IndexingThread.run() COMPLETED ===")
            logger.info(f"Results: {results}")
            logger.info(f"Emitting finished signal...")
            self.finished.emit(results)
            logger.info("Finished signal emitted successfully")
            
        except Exception as e:
            error_msg = f"Indexing error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
    
    def stop(self, *, wait: bool = False) -> None:
        """Signal the thread to stop (graceful shutdown)."""
        logger.info("IndexingThread stop requested")
        self._should_stop = True
        if wait:
            self.wait()


class CancellableIndexingThread(IndexingThread):
    """
    Extended IndexingThread with pause/resume/cancel support.
    
    For future use: allows users to pause/resume long scans.
    v0.5.4+ feature.
    """
    
    paused = Signal()
    resumed = Signal()
    cancelled = Signal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_paused = False
    
    def pause(self):
        """Pause indexing (for future implementation)."""
        self._is_paused = True
        self.paused.emit()
        logger.info("Indexing paused")
    
    def resume(self):
        """Resume indexing (for future implementation)."""
        self._is_paused = False
        self.resumed.emit()
        logger.info("Indexing resumed")
    
    def cancel(self):
        """Cancel indexing and cleanup."""
        self._should_stop = True
        self.cancelled.emit()
        self.wait()
        logger.info("Indexing cancelled")
