from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Tuple

from PIL import Image
from photo_cleaner.config import AppConfig

logger = logging.getLogger(__name__)

# Register HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # pillow-heif not available, HEIC files will fail


def _cache_dir() -> Path:
    # MSI installs under Program Files are read-only for normal users.
    # Always use per-user writable app cache location.
    d = AppConfig.get_cache_dir() / "thumbnails"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _thumb_path(image_path: Path, size: Tuple[int, int]) -> Path:
    st = image_path.stat()
    key = f"{image_path.resolve()}|{st.st_mtime}|{st.st_size}|{size[0]}x{size[1]}"
    name = hashlib.sha1(key.encode()).hexdigest() + ".png"
    return _cache_dir() / name


def get_thumbnail(image_path: Path, size: Tuple[int, int]) -> Path:
    """Return path to cached thumbnail, creating it if necessary.

    Args:
        image_path: source image path
        size: (width, height) in pixels

    Returns:
        Path to PNG thumbnail on disk
    """
    image_path = Path(image_path)
    thumb = _thumb_path(image_path, size)
    if thumb.exists():
        return thumb

    try:
        with Image.open(image_path) as im:
            im.convert("RGBA")
            im.thumbnail(size, Image.LANCZOS)
            im.save(thumb, format="PNG")
    except (OSError, IOError) as e:
        # On error, if there is an existing corrupt file, remove it and re-raise
        if thumb.exists():
            try:
                thumb.unlink()
            except OSError:
                pass
        raise
    except (ValueError, RuntimeError, AttributeError) as e:
        # Unexpected error during thumbnail generation
        logger.error(f"Unexpected error generating thumbnail: {e}", exc_info=True)
        if thumb.exists():
            try:
                thumb.unlink()
            except OSError:
                pass
        raise

    return thumb


def get_thumbnail_size(image_path: Path, size: Tuple[int, int]):
    """Helper that creates/returns thumbnail path for given size. Kept for compatibility."""
    return get_thumbnail(image_path, size)
