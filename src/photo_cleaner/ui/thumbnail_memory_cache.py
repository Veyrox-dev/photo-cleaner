"""
P5.4: Thumbnail Memory Cache with LRU Eviction

In-memory QPixmap cache for thumbnails with size limits to prevent OOM.
Uses Least Recently Used (LRU) eviction when cache exceeds max size.

Design:
- Store QPixmap objects in memory for fast UI rendering
- Max 1000 pixmaps or ~500MB (whichever hits first)
- Automatically evict least recently used items when full
- Thread-safe operations via locks

Benefits:
- Faster UI scrolling (no disk reads)
- Prevents OOM by capping memory usage
- Transparent to UI code (drop-in cache)
"""

import logging
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ThumbnailMemoryCache:
    """
    Thread-safe LRU cache for QPixmap thumbnails.
    
    Features:
    - Max 1000 pixmaps in cache
    - Max ~500MB memory usage
    - Automatic LRU eviction
    - Thread-safe operations
    """
    
    MAX_PIXMAPS = 1000  # P5.4: Maximum pixmaps to cache
    MAX_MEMORY_MB = 500  # Rough estimate: 1000 * 500KB
    BYTES_PER_MB = 1024 * 1024
    
    def __init__(self):
        """Initialize empty LRU cache."""
        self._cache: OrderedDict[str, tuple] = OrderedDict()  # {key: (pixmap, size_bytes)}
        self._lock = RLock()
        self._total_bytes = 0
        self._hits = 0
        self._misses = 0
    
    def _cache_key(self, image_path: Path, size: Tuple[int, int]) -> str:
        """Generate cache key from path and size."""
        return f"{image_path}|{size[0]}x{size[1]}"
    
    def get(self, image_path: Path, size: Tuple[int, int]) -> Optional[object]:
        """
        Get pixmap from cache.
        
        Args:
            image_path: Path to source image
            size: Thumbnail (width, height)
            
        Returns:
            QPixmap if cached, None otherwise
        """
        key = self._cache_key(image_path, size)
        
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                pixmap, _ = self._cache[key]
                self._hits += 1
                return pixmap
            
            self._misses += 1
            return None
    
    def put(self, image_path: Path, size: Tuple[int, int], pixmap: object, size_bytes: int = 100000) -> None:
        """
        Put pixmap in cache.
        
        Args:
            image_path: Path to source image
            size: Thumbnail (width, height)
            pixmap: QPixmap object to cache
            size_bytes: Estimated size in bytes (default 100KB)
        """
        key = self._cache_key(image_path, size)
        max_bytes = self.MAX_MEMORY_MB * self.BYTES_PER_MB
        
        with self._lock:
            # Remove old entry if exists
            if key in self._cache:
                _, old_size = self._cache[key]
                self._total_bytes -= old_size
                del self._cache[key]

            # Skip caching if incoming item alone exceeds the cache budget
            if size_bytes >= max_bytes:
                logger.warning("Skip caching oversized thumbnail (exceeds memory budget)")
                return
            
            # Check if we need to evict entries
            while self._cache and (
                len(self._cache) >= self.MAX_PIXMAPS
                or self._total_bytes + size_bytes > max_bytes
            ):
                old_key, (_, old_size) = self._cache.popitem(last=False)
                self._total_bytes -= old_size
                logger.debug(f"Evicted from thumbnail cache: {old_key}")
            
            # Add new entry
            self._cache[key] = (pixmap, size_bytes)
            self._total_bytes += size_bytes
            
            logger.debug(
                f"Cached thumbnail: {len(self._cache)}/{self.MAX_PIXMAPS} pixmaps, "
                f"{self._total_bytes // self.BYTES_PER_MB}MB"
            )
    
    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._total_bytes = 0
            logger.info(f"Cleared thumbnail cache ({count} entries)")
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            hit_rate = (
                self._hits / (self._hits + self._misses)
                if (self._hits + self._misses) > 0
                else 0
            )
            return {
                'pixmaps': len(self._cache),
                'memory_mb': self._total_bytes // self.BYTES_PER_MB,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': f"{hit_rate:.1%}",
            }


# Global singleton instance
_thumbnail_cache: Optional[ThumbnailMemoryCache] = None


def get_thumbnail_memory_cache() -> ThumbnailMemoryCache:
    """Get or create global thumbnail cache instance."""
    global _thumbnail_cache
    if _thumbnail_cache is None:
        _thumbnail_cache = ThumbnailMemoryCache()
        logger.info("Initialized global thumbnail memory cache")
    return _thumbnail_cache
