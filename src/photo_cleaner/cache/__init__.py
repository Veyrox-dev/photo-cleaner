"""
Cache module for PhotoCleaner.

Provides persistent caching of image analysis results to avoid redundant
MediaPipe analysis on subsequent scans.

Components:
- ImageCacheManager: Main cache management class
- CacheEntry: Data class for cache entries
- CacheStats: Statistics tracking
- CLI: Command-line interface for cache management
- CacheManagementDialog: GUI dialog for cache control
"""

from photo_cleaner.cache.image_cache_manager import (
    ImageCacheManager,
    CacheEntry,
    CacheStats,
    CacheQueryBuilder,
)

__all__ = [
    "ImageCacheManager",
    "CacheEntry",
    "CacheStats",
    "CacheQueryBuilder",
]
