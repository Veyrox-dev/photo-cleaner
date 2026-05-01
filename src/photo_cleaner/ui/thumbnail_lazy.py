from __future__ import annotations

import time
from dataclasses import dataclass
import logging
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, Tuple, Dict

from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import QListWidget, QAbstractItemView, QListWidgetItem, QApplication


logger = logging.getLogger(__name__)


class SmartThumbnailCache:
    """Memory-aware thumbnail cache storing QImage thumbnails.

    Stores QImage objects keyed by (path, size). Limits total memory by LRU.
    """

    def __init__(self, max_size_mb: int = 100):
        self.cache: Dict[str, tuple[QImage, int, int]] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        self.access_counter = 0

    def _key(self, image_path: Path, size: Tuple[int, int]) -> str:
        return f"{image_path}::{size[0]}x{size[1]}"

    def estimate_image_size(self, img: QImage) -> int:
        if img.isNull():
            return 0
        # Approximate bytes: width * height * 4 (ARGB32)
        return int(img.width() * img.height() * 4)

    def get(self, image_path: Path, size: Tuple[int, int]) -> Optional[QImage]:
        key = self._key(image_path, size)
        val = self.cache.get(key)
        if not val:
            return None
        img, _, sz = val
        self.access_counter += 1
        self.cache[key] = (img, self.access_counter, sz)
        return img

    def put(self, image_path: Path, size: Tuple[int, int], img: QImage) -> None:
        if img.isNull():
            return
        key = self._key(image_path, size)
        sz = self.estimate_image_size(img)
        # Evict if needed
        if self.current_size + sz > self.max_size_bytes:
            self._evict_to(self.max_size_bytes - sz)
        self.access_counter += 1
        self.cache[key] = (img, self.access_counter, sz)
        self.current_size += sz

    def _evict_to(self, target_free: int) -> None:
        # Evict least recently used until we have enough room
        if target_free <= 0:
            return
        # Sort by access counter (ascending = oldest)
        items = sorted(self.cache.items(), key=lambda kv: kv[1][1])
        freed = 0
        for k, (img, acc, sz) in items:
            del self.cache[k]
            freed += sz
            self.current_size -= sz
            if freed >= target_free:
                break


class ThumbnailLoader(QThread):
    """Background QThread that loads QImage thumbnails.

    Emits thumbnails as QImage for thread-safety; UI converts to QPixmap.
    """

    thumbnail_loaded = Signal(int, QImage)  # index, image
    thumbnail_loaded_with_path = Signal(int, QImage, str)  # index, image, source path

    def __init__(self, cache: SmartThumbnailCache, thumb_size: Tuple[int, int] = (200, 200)):
        super().__init__()
        self.queue: "Queue[tuple[int, Path]]" = Queue()
        self.running = True
        self.paused = True  # ✅ NEW: Start paused (only activate in _finish_post_indexing)
        self.cache = cache
        self.thumb_size = thumb_size

    def enqueue(self, index: int, image_path: Path) -> None:
        self.queue.put((index, image_path))

    def clear_queue(self) -> None:
        """Clear all pending thumbnail requests from queue.
        
        Prevents race condition where old thumbnails are loaded after refresh_groups()
        which would cause "invalid index" warnings when callbacks return.
        """
        cleared = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                cleared += 1
            except Empty:
                break
        if cleared > 0:
            logger.info(f"[THUMB] Cleared {cleared} pending thumbnail requests from queue")

    def pause(self) -> None:
        """Pause thumbnail loading without stopping the thread."""
        self.paused = True

    def resume(self) -> None:
        """Resume thumbnail loading."""
        self.paused = False

    def stop(self) -> None:
        self.running = False

    def run(self) -> None:
        logger.info("[THUMB] ThumbnailLoader thread started")
        while self.running:
            # ✅ NEW: Check paused flag - loop continues but skips processing
            if self.paused:
                import time
                time.sleep(0.1)  # Small sleep to avoid busy-waiting
                continue
            
            try:
                index, image_path = self.queue.get(timeout=0.1)
            except Empty:
                continue
            logger.debug(f"[THUMB] Loading thumbnail index={index} path={image_path}")
            img = self._load_or_generate(image_path, self.thumb_size)
            logger.debug(f"[THUMB] Emitting thumbnail index={index} size={img.width()}x{img.height()}")
            self.thumbnail_loaded.emit(index, img)
            self.thumbnail_loaded_with_path.emit(index, img, str(image_path))

    def _load_or_generate(self, image_path: Path, size: Tuple[int, int]) -> QImage:
        # Try cache
        cached = self.cache.get(image_path, size)
        if cached is not None and not cached.isNull():
            return cached
        # Load and scale via QImage (thread-safe). Fallback to PIL for HEIC/unsupported formats.
        qimg = QImage()
        if qimg.load(str(image_path)):
            thumb = qimg.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cache.put(image_path, size, thumb)
            return thumb

        try:
            from PIL import Image
            with Image.open(image_path) as im:
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGBA")
                im.thumbnail(size, Image.LANCZOS)
                if im.mode != "RGBA":
                    im = im.convert("RGBA")
                data = im.tobytes("raw", "RGBA")
                qimg = QImage(data, im.width, im.height, QImage.Format_RGBA8888).copy()
                if qimg.isNull():
                    return self._placeholder(size)
                self.cache.put(image_path, size, qimg)
                return qimg
        except (OSError, ValueError, RuntimeError) as e:
            logger.debug(f"[THUMB] PIL fallback failed for {image_path}: {e}")
            return self._placeholder(size)

    def _placeholder(self, size: Tuple[int, int]) -> QImage:
        img = QImage(size[0], size[1], QImage.Format_ARGB32)
        img.fill(Qt.darkGray)
        return img


class ThumbnailListView(QListWidget):
    """Lazy-loading QListWidget optimized for large image sets."""

    def __init__(self, thumb_size: Tuple[int, int] = (200, 200), cache_mb: int = 100):
        super().__init__()
        # View tuning
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSpacing(6)
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setUniformItemSizes(True)
        self.setIconSize(QSize(thumb_size[0], thumb_size[1]))

        # State
        self.thumb_size = thumb_size
        self.visible_indexes: set[int] = set()
        self.loaded_indexes: set[int] = set()
        self.max_loaded: int = 200  # cap loaded items to avoid memory spikes

        # Cache and loader
        self.cache = SmartThumbnailCache(max_size_mb=cache_mb)
        self.loader = ThumbnailLoader(self.cache, thumb_size=thumb_size)
        self.loader.thumbnail_loaded.connect(self._on_thumb_loaded)
        self.loader.start()

        # Scroll hook
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def closeEvent(self, event) -> None:
        try:
            self.loader.stop()
            self.loader.wait(500)
        except (RuntimeError, AttributeError):
            pass
        super().closeEvent(event)

    def set_image_list(self, image_paths: list[Path]) -> None:
        self.clear()
        for i, p in enumerate(image_paths):
            item = QListWidgetItem()
            # Placeholder icon (empty pixmap)
            placeholder = QPixmap(self.thumb_size[0], self.thumb_size[1])
            placeholder.fill(Qt.black)
            item.setIcon(QIcon(placeholder))
            item.setData(Qt.UserRole, str(p))
            item.setSizeHint(QSize(self.thumb_size[0] + 16, self.thumb_size[1] + 28))
            self.addItem(item)
        # Trigger initial load for visible range
        QApplication.processEvents()
        self._on_scroll()

    def _on_scroll(self) -> None:
        # Compute visible rect and indexes
        vp = self.viewport().rect()
        visible = []
        for i in range(self.count()):
            rect = self.visualItemRect(self.item(i))
            if vp.intersects(rect):
                visible.append(i)
        # Enqueue loads for visible items
        for i in visible:
            if i not in self.loaded_indexes:
                path_str = self.item(i).data(Qt.UserRole)
                if path_str:
                    self.loader.enqueue(i, Path(path_str))
                    self.loaded_indexes.add(i)
        # Unload distant items if over cap
        if len(self.loaded_indexes) > self.max_loaded:
            to_remove = list(sorted(self.loaded_indexes - set(visible)))
            # Remove oldest first
            for i in to_remove[: max(0, len(self.loaded_indexes) - self.max_loaded)]:
                self._unload_index(i)

    def _on_thumb_loaded(self, index: int, qimg: QImage) -> None:
        # Convert to pixmap in UI thread
        if index < 0 or index >= self.count():
            return
        pm = QPixmap.fromImage(qimg)
        self.item(index).setIcon(QIcon(pm))

    def _unload_index(self, index: int) -> None:
        if index < 0 or index >= self.count():
            return
        # Reset to placeholder to free icon pixmap
        placeholder = QPixmap(self.thumb_size[0], self.thumb_size[1])
        placeholder.fill(Qt.black)
        self.item(index).setIcon(QIcon(placeholder))
        if index in self.loaded_indexes:
            self.loaded_indexes.remove(index)
