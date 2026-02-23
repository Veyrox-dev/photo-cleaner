"""
File scanner for photo collections.

Recursively scans directories and identifies image files.
"""

import logging
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
    ".heic",
    ".heif",
}


class FileScanner:
    """Recursively scans directories for image files."""

    def __init__(self, root_path: Path, extensions: set[str] | None = None) -> None:
        """
        Initialize file scanner.

        Args:
            root_path: Root directory to scan
            extensions: Set of file extensions to include (default: SUPPORTED_EXTENSIONS)
        """
        self.root_path = Path(root_path)
        self.extensions = extensions or SUPPORTED_EXTENSIONS
        self._normalize_extensions()

    def _normalize_extensions(self) -> None:
        """Ensure all extensions are lowercase and start with a dot."""
        self.extensions = {
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in self.extensions
        }

    def scan(self) -> Generator[Path, None, None]:
        """
        Recursively scan for image files.

        Yields:
            Path objects for each discovered image file

        Raises:
            ValueError: If root_path doesn't exist or isn't a directory
        """
        if not self.root_path.exists():
            raise ValueError(f"Path does not exist: {self.root_path}")

        if not self.root_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.root_path}")

        logger.info(f"Starting scan of {self.root_path}")
        count = 0

        try:
            for path in self.root_path.rglob("*"):
                if path.is_file() and path.suffix.lower() in self.extensions:
                    count += 1
                    if count % 100 == 0:
                        logger.debug(f"Scanned {count} files...")
                    yield path
        except PermissionError as e:
            logger.warning(f"Permission denied: {e}")
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            raise

        logger.info(f"Scan complete. Found {count} image files")

    def count_files(self) -> int:
        """
        Count total number of image files without yielding them.

        Returns:
            Total count of image files
        """
        return sum(1 for _ in self.scan())