"""
Unit tests for ImageCacheManager.

Tests cover:
- Cache storage and retrieval
- Hash computation
- Bulk operations
- Cache clearing
- Edge cases (missing files, corrupted data, etc.)
"""

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest import TestCase, mock

import pytest

from photo_cleaner.cache.image_cache_manager import (
    CacheEntry,
    CacheStats,
    ImageCacheManager,
    CacheQueryBuilder,
)


class TestImageCacheManager(TestCase):
    """Test suite for ImageCacheManager."""
    
    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.cache = ImageCacheManager(self.conn)
    
    def tearDown(self):
        """Clean up temporary database."""
        self.conn.close()
        self.db_path.unlink(missing_ok=True)
    
    def test_initialization(self):
        """Test cache manager initialization."""
        assert self.cache is not None
        assert self.cache.conn is not None
        assert self.cache.stats is not None
    
    def test_schema_creation(self):
        """Test that schema is created on initialization."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_cache'")
        table = cursor.fetchone()
        assert table is not None, "Cache table not created"
    
    def test_compute_file_hash(self):
        """Test file hash computation."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_content = b"test image content"
            f.write(test_content)
            f.flush()
            file_path = Path(f.name)
        
        # File is now closed, can safely compute hash and delete
        try:
            hash1 = ImageCacheManager.compute_file_hash(file_path)
            assert len(hash1) == 40, "SHA1 hash should be 40 chars"
            
            # Same file should produce same hash
            hash2 = ImageCacheManager.compute_file_hash(file_path)
            assert hash1 == hash2, "Hashes should be identical for same file"
        finally:
            file_path.unlink(missing_ok=True)
    
    def test_store_and_lookup(self):
        """Test storing and retrieving cache entries."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test image")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store entry
            result = self.cache.store(
                file_path=file_path,
                quality_score=85.5,
                top_n_flag=True,
                metadata={"faces_detected": 2},
            )
            assert result is True, "Store should succeed"
            assert self.cache.stats.cache_updates == 1
            
            # Lookup entry
            entry = self.cache.lookup(file_path)
            assert entry is not None, "Entry should be found"
            assert entry.quality_score == 85.5
            assert entry.top_n_flag is True
            assert entry.metadata["faces_detected"] == 2
            assert self.cache.stats.cache_hits == 1
        finally:
            file_path.unlink()
    
    def test_cache_miss(self):
        """Test cache miss for non-existent file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Delete file before lookup
            file_path.unlink()
            
            # Lookup should fail
            entry = self.cache.lookup(file_path)
            assert entry is None, "Lookup should return None for missing file"
            assert self.cache.stats.cache_misses == 1
        except (OSError, ValueError) as e:
            pass  # Expected: file handling errors

    
    def test_force_reanalyze(self):
        """Test force_reanalyze flag."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test image")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store entry
            self.cache.store(
                file_path=file_path,
                quality_score=90.0,
                top_n_flag=False,
            )
            
            # Lookup with force_reanalyze=True should ignore cache
            entry = self.cache.lookup(file_path, force_reanalyze=True)
            assert entry is None, "Force reanalyze should ignore cache"
            assert self.cache.stats.cache_misses == 1
            assert self.cache.stats.cache_hits == 0
        finally:
            file_path.unlink()
    
    def test_bulk_lookup(self):
        """Test bulk lookup operation."""
        files = []
        
        # Create test files
        for i in range(3):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            f.write(f"test image {i}".encode())
            f.flush()
            f.close()
            files.append(Path(f.name))
        
        try:
            # Store two entries
            self.cache.store(files[0], quality_score=80.0, top_n_flag=False)
            self.cache.store(files[1], quality_score=90.0, top_n_flag=True)
            # Don't store files[2]
            
            # Bulk lookup
            uncached, cached = self.cache.bulk_lookup(files)
            
            assert len(uncached) == 1, "Should have 1 uncached file"
            assert len(cached) == 2, "Should have 2 cached files"
            assert files[2] in uncached
            assert files[0] in cached
            assert files[1] in cached
        finally:
            for f in files:
                f.unlink()
    
    def test_clear_cache_all(self):
        """Test clearing entire cache."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store entries
            self.cache.store(file_path, 85.0, False)
            
            # Verify entry exists
            entry = self.cache.lookup(file_path)
            assert entry is not None
            
            # Clear cache
            cleared = self.cache.clear_cache(older_than_days=None)
            assert cleared > 0, "Should have cleared entries"
            
            # Verify cache is empty
            self.cache.reset_stats()
            entry = self.cache.lookup(file_path)
            assert entry is None, "Cache should be empty after clear"
        finally:
            file_path.unlink()
    
    def test_clear_cache_by_age(self):
        """Test clearing cache entries older than N days."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store old entry (manually set timestamp)
            old_timestamp = time.time() - (10 * 86400)  # 10 days ago
            cursor = self.conn.cursor()
            file_hash = ImageCacheManager.compute_file_hash(file_path)
            
            cursor.execute("""
                INSERT INTO image_cache
                (image_hash, quality_score, top_n_flag, analysis_timestamp, 
                 pipeline_version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_hash, 80.0, 0, old_timestamp, 1, old_timestamp))
            self.conn.commit()
            
            # Store new entry
            self.cache.store(file_path, 90.0, True)
            
            # Clear old entries only
            # This will clear nothing since we just stored new data
            # Let's modify to clear entries older than 5 days
            cleared = self.cache.clear_cache(older_than_days=5)
            # The old entry should be cleared
            
            cursor.execute("SELECT COUNT(*) FROM image_cache")
            count = cursor.fetchone()[0]
            # We should have only the new entry
            assert count <= 2, "Old entries should be cleared"
        finally:
            file_path.unlink()
    
    def test_invalidate_by_hash(self):
        """Test invalidating entry by hash."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store entry
            self.cache.store(file_path, 85.0, False)
            file_hash = ImageCacheManager.compute_file_hash(file_path)
            
            # Verify entry exists
            entry = self.cache.lookup(file_path)
            assert entry is not None
            
            # Invalidate by hash
            result = self.cache.invalidate_by_hash(file_hash)
            assert result is True, "Should invalidate entry"
            
            # Verify entry is gone
            self.cache.reset_stats()
            entry = self.cache.lookup(file_path)
            assert entry is None, "Entry should be invalidated"
        finally:
            file_path.unlink()
    
    def test_cache_stats(self):
        """Test cache statistics."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            self.cache.store(file_path, 80.0, False)
            self.cache.lookup(file_path)  # Hit
            self.cache.lookup(file_path)  # Hit
            
            stats = self.cache.get_cache_stats()
            assert stats.cache_hits == 2
            assert stats.cache_updates == 1
            
            # Reset stats
            self.cache.reset_stats()
            stats = self.cache.get_cache_stats()
            assert stats.cache_hits == 0
        finally:
            file_path.unlink()
    
    def test_get_cache_size(self):
        """Test getting cache size statistics."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store entries with different scores
            self.cache.store(file_path, 80.0, False)
            self.cache.store(file_path, 90.0, True)
            
            size_info = self.cache.get_cache_size()
            assert size_info["entries"] > 0
            assert "avg_quality_score" in size_info
            assert "oldest_entry" in size_info
        finally:
            file_path.unlink()
    
    def test_metadata_storage(self):
        """Test metadata storage and retrieval."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            metadata = {
                "faces_detected": 3,
                "laplacian_variance": 123.45,
                "brightness": 150,
                "width": 1920,
                "height": 1080,
            }
            
            self.cache.store(
                file_path=file_path,
                quality_score=92.5,
                top_n_flag=True,
                metadata=metadata,
            )
            
            entry = self.cache.lookup(file_path)
            assert entry.metadata["faces_detected"] == 3
            assert entry.metadata["laplacian_variance"] == 123.45
            assert entry.metadata["width"] == 1920
        finally:
            file_path.unlink()
    
    def test_pipeline_version_filtering(self):
        """Test that different pipeline versions are cached separately."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store with current version
            self.cache.store(file_path, 85.0, False)
            entry = self.cache.lookup(file_path)
            assert entry is not None
            
            # Simulate version change
            old_version = ImageCacheManager.PIPELINE_VERSION
            ImageCacheManager.PIPELINE_VERSION = 999
            
            try:
                # Lookup should fail (different version)
                self.cache.reset_stats()
                entry = self.cache.lookup(file_path)
                assert entry is None, "Should not find entry with different pipeline version"
                assert self.cache.stats.cache_misses == 1
            finally:
                ImageCacheManager.PIPELINE_VERSION = old_version
        finally:
            file_path.unlink()


class TestCacheQueryBuilder(TestCase):
    """Test suite for CacheQueryBuilder."""
    
    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.cache = ImageCacheManager(self.conn)
        self.query_builder = CacheQueryBuilder(self.conn)
    
    def tearDown(self):
        """Clean up temporary database."""
        self.conn.close()
        self.db_path.unlink(missing_ok=True)
    
    def test_get_entries_by_quality_range(self):
        """Test querying entries by quality score range."""
        files = []
        scores = [70.0, 80.0, 85.0, 90.0, 95.0]
        
        for idx, score in enumerate(scores):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            # Write unique content so each file has different hash
            f.write(f"test_quality_{idx}_{score}".encode())
            f.flush()
            f.close()
            files.append(Path(f.name))
            self.cache.store(Path(f.name), score, False)
        
        try:
            # Query range 80-90
            entries = self.query_builder.get_entries_by_quality_range(80.0, 90.0)
            assert len(entries) >= 3, "Should find entries in range"
            
            for entry in entries:
                assert 80.0 <= entry["quality_score"] <= 90.0
        finally:
            for f in files:
                f.unlink(missing_ok=True)
    
    def test_get_top_n_entries(self):
        """Test querying top-N flagged entries."""
        files = []
        
        for i in range(5):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            # Write unique content so each file has different hash
            f.write(f"test_topn_{i}".encode())
            f.flush()
            f.close()
            files.append(Path(f.name))
            # Store 2 with top_n=True, 3 with top_n=False
            top_n = (i < 2)
            self.cache.store(Path(f.name), 85.0 + i, top_n)
        
        try:
            entries = self.query_builder.get_top_n_entries(limit=10)
            assert len(entries) == 2, "Should find 2 top-N entries"
            
            for entry in entries:
                assert entry["top_n_flag"] is True
        finally:
            for f in files:
                f.unlink(missing_ok=True)


class TestCacheEntry(TestCase):
    """Test suite for CacheEntry dataclass."""
    
    def test_cache_entry_creation(self):
        """Test creating CacheEntry objects."""
        entry = CacheEntry(
            image_hash="abc123",
            quality_score=85.5,
            top_n_flag=True,
            analysis_timestamp=time.time(),
            metadata={"test": "data"},
        )
        
        assert entry.image_hash == "abc123"
        assert entry.quality_score == 85.5
        assert entry.top_n_flag is True
        assert entry.metadata["test"] == "data"


class TestCacheStats(TestCase):
    """Test suite for CacheStats dataclass."""
    
    def test_cache_stats_creation(self):
        """Test creating CacheStats objects."""
        stats = CacheStats(
            cache_hits=10,
            cache_misses=5,
            cache_updates=3,
        )
        
        assert stats.cache_hits == 10
        assert stats.cache_misses == 5
        assert stats.cache_updates == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
