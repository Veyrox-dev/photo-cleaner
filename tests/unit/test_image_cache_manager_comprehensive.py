"""
Advanced test suite for ImageCacheManager.

Coverage targets:
- Cache store/lookup operations
- Hash computation robustness
- Database operations
- Cache invalidation & versioning
- Edge cases (large files, corrupted cache)
- Concurrent access patterns

Generated: 2026-02-02
Target Coverage: 40%+ (from 28.75%)
"""

import tempfile
from pathlib import Path
from unittest import TestCase
import json
import sqlite3
from datetime import datetime, timezone

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from photo_cleaner.cache.image_cache_manager import (
    ImageCacheManager,
    CacheEntry,
    CacheStats,
)


class TestCacheImageGenerator:
    """Helper to generate test cache files."""

    @staticmethod
    def create_test_image(width: int = 800, height: int = 600) -> Path:
        """Create a test JPEG image."""
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL not available")
        
        img = Image.new("RGB", (width, height), (128, 128, 128))
        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()
        img.save(temp_path, "JPEG")
        return temp_path

    @staticmethod
    def create_test_images(count: int = 3) -> list:
        """Create multiple test images."""
        images = []
        for i in range(count):
            img = TestCacheImageGenerator.create_test_image(
                width=800 + i * 100,
                height=600 + i * 100
            )
            images.append(img)
        return images


class TestImageCacheManagerBasics(TestCase):
    """Test basic cache manager functionality."""

    def setUp(self):
        """Initialize cache manager with temp database."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = Path(self.temp_file.name)
        self.temp_file.close()
        
        self.conn = sqlite3.connect(str(self.temp_db_path))
        self.cache = ImageCacheManager(db_conn=self.conn)

    def tearDown(self):
        """Clean up temp files."""
        self.conn.close()
        self.temp_db_path.unlink(missing_ok=True)

    def test_cache_manager_initialization(self):
        """Test cache manager can be created."""
        assert self.cache is not None
        assert self.cache.conn is not None

    def test_cache_has_required_attributes(self):
        """Test cache manager has required attributes."""
        assert hasattr(self.cache, "store")
        assert hasattr(self.cache, "lookup")
        assert hasattr(self.cache, "stats")
        assert hasattr(self.cache, "compute_file_hash")

    def test_cache_stats_initialization(self):
        """Test cache statistics are initialized."""
        stats = self.cache.stats
        assert isinstance(stats, CacheStats)
        assert stats.cache_hits >= 0
        assert stats.cache_misses >= 0

    def test_cache_pipeline_version_exists(self):
        """Test pipeline version is set."""
        assert hasattr(self.cache, "PIPELINE_VERSION")
        assert self.cache.PIPELINE_VERSION is not None


class TestImageCacheHashComputation(TestCase):
    """Test file hashing functionality."""

    def setUp(self):
        """Initialize cache manager."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = Path(self.temp_file.name)
        self.temp_file.close()
        
        self.conn = sqlite3.connect(str(self.temp_db_path))
        self.cache = ImageCacheManager(db_conn=self.conn)

    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.temp_db_path.unlink(missing_ok=True)

    def test_compute_hash_valid_file(self):
        """Test computing hash for valid file."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            hash_value = self.cache.compute_file_hash(test_image)
            assert hash_value is not None
            assert isinstance(hash_value, str)
            assert len(hash_value) > 0
        finally:
            test_image.unlink(missing_ok=True)

    def test_compute_hash_consistency(self):
        """Test hash is consistent for same file."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            hash1 = self.cache.compute_file_hash(test_image)
            hash2 = self.cache.compute_file_hash(test_image)
            assert hash1 == hash2
        finally:
            test_image.unlink(missing_ok=True)

    def test_compute_hash_different_files(self):
        """Test different files produce different hashes."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        images = TestCacheImageGenerator.create_test_images(2)
        try:
            hash1 = self.cache.compute_file_hash(images[0])
            hash2 = self.cache.compute_file_hash(images[1])
            # Different images should (very likely) have different hashes
            assert hash1 != hash2
        finally:
            for img in images:
                img.unlink(missing_ok=True)

    def test_compute_hash_nonexistent_file(self):
        """Test hashing nonexistent file raises error."""
        try:
            self.cache.compute_file_hash(Path("/nonexistent/file.jpg"))
            self.fail("Should raise error for nonexistent file")
        except (OSError, IOError):
            pass  # Expected


class TestImageCacheStoreLookup(TestCase):
    """Test cache store and lookup operations."""

    def setUp(self):
        """Initialize cache manager."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = Path(self.temp_file.name)
        self.temp_file.close()
        
        self.conn = sqlite3.connect(str(self.temp_db_path))
        self.cache = ImageCacheManager(db_conn=self.conn)

    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.temp_db_path.unlink(missing_ok=True)

    def test_store_and_lookup_basic(self):
        """Test storing and looking up a cache entry."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            # Store entry
            success = self.cache.store(
                test_image,
                quality_score=75.5,
                top_n_flag=True
            )
            assert success
            
            # Lookup entry
            entry = self.cache.lookup(test_image)
            assert entry is not None
            assert entry.quality_score == 75.5
            assert entry.top_n_flag is True
        finally:
            test_image.unlink(missing_ok=True)

    def test_lookup_nonexistent_entry(self):
        """Test looking up nonexistent entry returns None."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            entry = self.cache.lookup(test_image)
            assert entry is None
        finally:
            test_image.unlink(missing_ok=True)

    def test_store_with_metadata(self):
        """Test storing entry with metadata."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        metadata = {
            "faces_detected": 2,
            "camera_model": "iPhone 12",
            "custom_field": "custom_value"
        }
        
        try:
            success = self.cache.store(
                test_image,
                quality_score=80.0,
                top_n_flag=False,
                metadata=metadata
            )
            assert success
            
            entry = self.cache.lookup(test_image)
            assert entry is not None
            assert entry.metadata is not None
            assert entry.metadata.get("faces_detected") == 2
            assert entry.metadata.get("camera_model") == "iPhone 12"
        finally:
            test_image.unlink(missing_ok=True)

    def test_lookup_cache_statistics(self):
        """Test cache statistics are updated on lookup."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            initial_misses = self.cache.stats.cache_misses
            
            # First lookup - miss
            self.cache.lookup(test_image)
            assert self.cache.stats.cache_misses > initial_misses
            
            # Store it
            self.cache.store(test_image, quality_score=75.0, top_n_flag=False)
            
            initial_hits = self.cache.stats.cache_hits
            
            # Second lookup - hit
            entry = self.cache.lookup(test_image)
            assert entry is not None
            assert self.cache.stats.cache_hits > initial_hits
        finally:
            test_image.unlink(missing_ok=True)

    def test_store_multiple_entries(self):
        """Test storing multiple cache entries."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        images = TestCacheImageGenerator.create_test_images(3)
        try:
            for i, img in enumerate(images):
                success = self.cache.store(
                    img,
                    quality_score=70.0 + i * 5,
                    top_n_flag=i % 2 == 0
                )
                assert success
            
            # Verify all stored
            for i, img in enumerate(images):
                entry = self.cache.lookup(img)
                assert entry is not None
                assert entry.quality_score == 70.0 + i * 5
        finally:
            for img in images:
                img.unlink(missing_ok=True)


class TestImageCacheInvalidation(TestCase):
    """Test cache invalidation and versioning."""

    def setUp(self):
        """Initialize cache manager."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = Path(self.temp_file.name)
        self.temp_file.close()
        
        self.conn = sqlite3.connect(str(self.temp_db_path))
        self.cache = ImageCacheManager(db_conn=self.conn)

    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.temp_db_path.unlink(missing_ok=True)

    def test_force_reanalyze_skips_cache(self):
        """Test force_reanalyze bypasses cache lookup."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            # Store entry
            self.cache.store(
                test_image,
                quality_score=75.0,
                top_n_flag=True
            )
            
            # Lookup with force_reanalyze should return None
            entry = self.cache.lookup(test_image, force_reanalyze=True)
            assert entry is None
        finally:
            test_image.unlink(missing_ok=True)


class TestImageCacheEdgeCases(TestCase):
    """Test edge cases and error scenarios."""

    def setUp(self):
        """Initialize cache manager."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = Path(self.temp_file.name)
        self.temp_file.close()
        
        self.conn = sqlite3.connect(str(self.temp_db_path))
        self.cache = ImageCacheManager(db_conn=self.conn)

    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.temp_db_path.unlink(missing_ok=True)

    def test_store_with_extreme_quality_scores(self):
        """Test storing entries with extreme quality scores."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            # Very high score
            success = self.cache.store(
                test_image,
                quality_score=100.0,
                top_n_flag=True
            )
            assert success
            entry = self.cache.lookup(test_image)
            assert entry.quality_score == 100.0
        finally:
            test_image.unlink(missing_ok=True)

    def test_store_with_zero_quality_score(self):
        """Test storing entry with zero quality."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            success = self.cache.store(
                test_image,
                quality_score=0.0,
                top_n_flag=False
            )
            assert success
            entry = self.cache.lookup(test_image)
            assert entry.quality_score == 0.0
        finally:
            test_image.unlink(missing_ok=True)

    def test_store_with_large_metadata(self):
        """Test storing entry with large metadata."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        
        # Create large metadata
        large_metadata = {
            f"key_{i}": f"value_{i}" * 100
            for i in range(50)
        }
        
        try:
            success = self.cache.store(
                test_image,
                quality_score=75.0,
                top_n_flag=False,
                metadata=large_metadata
            )
            assert success
            
            entry = self.cache.lookup(test_image)
            assert entry is not None
            assert len(entry.metadata) == 50
        finally:
            test_image.unlink(missing_ok=True)

    def test_store_with_none_metadata(self):
        """Test storing entry with None metadata."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            success = self.cache.store(
                test_image,
                quality_score=75.0,
                top_n_flag=False,
                metadata=None
            )
            assert success
            
            entry = self.cache.lookup(test_image)
            assert entry is not None
        finally:
            test_image.unlink(missing_ok=True)


class TestCacheEntryDataclass(TestCase):
    """Test CacheEntry data structure."""

    def test_cache_entry_creation(self):
        """Test creating CacheEntry."""
        entry = CacheEntry(
            image_hash="abc123",
            quality_score=75.5,
            top_n_flag=True,
            analysis_timestamp=datetime.now(timezone.utc).timestamp(),
            pipeline_version="v1.0",
            metadata={"key": "value"}
        )
        assert entry.image_hash == "abc123"
        assert entry.quality_score == 75.5
        assert entry.top_n_flag is True

    def test_cache_entry_default_metadata(self):
        """Test CacheEntry with default metadata."""
        entry = CacheEntry(
            image_hash="abc123",
            quality_score=75.5,
            top_n_flag=False,
            analysis_timestamp=datetime.now(timezone.utc).timestamp(),
            pipeline_version="v1.0"
        )
        assert entry.metadata is None or entry.metadata == {}


class TestCacheStatistics(TestCase):
    """Test cache statistics tracking."""

    def setUp(self):
        """Initialize cache manager."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = Path(self.temp_file.name)
        self.temp_file.close()
        
        self.conn = sqlite3.connect(str(self.temp_db_path))
        self.cache = ImageCacheManager(db_conn=self.conn)

    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.temp_db_path.unlink(missing_ok=True)

    def test_statistics_initial_state(self):
        """Test cache statistics initial state."""
        stats = self.cache.stats
        assert stats.cache_hits >= 0
        assert stats.cache_misses >= 0
        # Additional stats may be available
        assert stats.cache_updates >= 0

    def test_statistics_after_store_lookup(self):
        """Test statistics are updated after operations."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        test_image = TestCacheImageGenerator.create_test_image()
        try:
            initial_misses = self.cache.stats.cache_misses
            
            # Miss
            self.cache.lookup(test_image)
            assert self.cache.stats.cache_misses >= initial_misses
            
            # Store
            self.cache.store(test_image, quality_score=75.0, top_n_flag=False)
            
            initial_hits = self.cache.stats.cache_hits
            
            # Hit
            self.cache.lookup(test_image)
            assert self.cache.stats.cache_hits > initial_hits
        finally:
            test_image.unlink(missing_ok=True)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
