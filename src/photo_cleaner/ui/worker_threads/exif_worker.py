from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from photo_cleaner.ui.exif_reader import ExifReader

logger = logging.getLogger(__name__)


class ExifWorkerThread(QThread):
    """Worker thread for async EXIF extraction."""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        """Execute EXIF extraction in background thread."""
        try:
            logger.debug("ExifWorkerThread: Reading EXIF for %s", self.file_path.name)
            exif_data = ExifReader.read_exif(self.file_path)
            logger.debug("ExifWorkerThread: EXIF read complete for %s", self.file_path.name)
            self.finished.emit(exif_data)
        except Exception as e:
            logger.error(
                "ExifWorkerThread: Failed to read EXIF for %s: %s",
                self.file_path.name,
                e,
                exc_info=True,
            )
            self.error.emit(str(e))
