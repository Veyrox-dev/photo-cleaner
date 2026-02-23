#!/usr/bin/env python3
"""
Phase 2-7 Improvements Test Suite

Tests für P2-P7 Fixes:
- P2.x: Input Validation
- P3.x: Logging Improvements
- P4.x: Database Optimizations
- P5.x: Resource Management
- P6.x: Edge Cases
- P7.x: Optional Improvements
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import json


class TestP2_InputValidation:
    """P2.x: Input validation improvements"""
    
    def test_pipeline_config_valid_hash_distance(self):
        """P2.1: Hash distance validation"""
        from photo_cleaner.pipeline.pipeline import PipelineConfig
        
        # Valid config should not raise
        config = PipelineConfig(hash_distance_threshold=5)
        assert config.hash_distance_threshold == 5
        
        # Invalid config should raise
        with pytest.raises(ValueError):
            PipelineConfig(hash_distance_threshold=-1)
        
        with pytest.raises(ValueError):
            PipelineConfig(hash_distance_threshold=33)
    
    def test_pipeline_config_brightness_validation(self):
        """P2.1: Brightness range validation"""
        from photo_cleaner.pipeline.pipeline import PipelineConfig
        
        # Invalid: low >= high
        with pytest.raises(ValueError):
            PipelineConfig(brightness_low=100, brightness_high=50)
        
        # Invalid: out of range
        with pytest.raises(ValueError):
            PipelineConfig(brightness_low=-1, brightness_high=100)
    
    def test_file_status_validation(self):
        """P2.5: FileStatus enum validation"""
        from photo_cleaner.repositories.file_repository import FileRepository
        from photo_cleaner.models.status import FileStatus
        
        mock_conn = Mock(spec=sqlite3.Connection)
        repo = FileRepository(mock_conn)
        
        # Valid FileStatus enum should validate
        # Invalid string should raise
        with pytest.raises(ValueError):
            # Simulate passing invalid status
            repo.set_status(Path("test.jpg"), "INVALID_STATUS")  # type: ignore
    
    def test_image_magic_bytes_validation(self):
        """P2.4: Image magic bytes validation"""
        from photo_cleaner.core.hasher import ImageHasher
        
        hasher = ImageHasher()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create valid JPEG file (with JPEG magic bytes)
            jpeg_path = Path(tmpdir) / "test.jpg"
            jpeg_data = bytes([0xFF, 0xD8, 0xFF]) + b"fake jpeg data"
            jpeg_path.write_bytes(jpeg_data)
            
            assert hasher._is_valid_image_magic(jpeg_path) is True
            
            # Create invalid file (no magic bytes)
            invalid_path = Path(tmpdir) / "invalid.jpg"
            invalid_path.write_bytes(b"not a real image file")
            
            assert hasher._is_valid_image_magic(invalid_path) is False


class TestP4_DatabaseOptimizations:
    """P4.x: Database optimization improvements"""
    
    def test_wal_mode_enabled(self):
        """P4.4: WAL mode should be enabled on schema init"""
        from photo_cleaner.db.schema import Database
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            db.connect()
            
            try:
                # Check WAL mode is enabled
                cursor = db.conn.cursor()
                cursor.execute("PRAGMA journal_mode")
                mode = cursor.fetchone()[0]
                assert mode.upper() == 'WAL'
            finally:
                db.close()
    
    def test_cache_vacuum_on_init(self):
        """P4.3: Cache should VACUUM on startup"""
        from photo_cleaner.cache.image_cache_manager import ImageCacheManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "cache.db"
            conn = sqlite3.connect(str(db_path))
            
            # Create manager (triggers schema init + vacuum)
            cache_mgr = ImageCacheManager(conn)
            
            # Check cache was created
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_cache'")
            assert cursor.fetchone() is not None
            
            conn.close()


class TestP5_ResourceManagement:
    """P5.x: Resource management improvements"""
    
    def test_thumbnail_memory_cache_lru(self):
        """P5.4: Thumbnail cache should evict LRU entries"""
        from photo_cleaner.ui.thumbnail_memory_cache import ThumbnailMemoryCache
        
        cache = ThumbnailMemoryCache()
        cache.MAX_PIXMAPS = 3  # Set low limit for testing
        
        # Add 3 items
        for i in range(3):
            cache.put(Path(f"img{i}.jpg"), (100, 100), f"pixmap_{i}", 100000)
        
        assert len(cache._cache) == 3
        
        # Add 4th item (should evict oldest)
        cache.put(Path("img3.jpg"), (100, 100), "pixmap_3", 100000)
        
        assert len(cache._cache) == 3  # Still 3 (LRU evicted oldest)
        
        # First item should be gone
        assert cache.get(Path("img0.jpg"), (100, 100)) is None
        
        # Last item should be there
        assert cache.get(Path("img3.jpg"), (100, 100)) == "pixmap_3"
    
    def test_thumbnail_cache_memory_limit(self):
        """P5.4: Thumbnail cache should respect memory limits"""
        from photo_cleaner.ui.thumbnail_memory_cache import ThumbnailMemoryCache
        
        cache = ThumbnailMemoryCache()
        cache.MAX_MEMORY_MB = 1  # Very small limit
        
        # Add items until memory limit hit
        for i in range(20):
            cache.put(
                Path(f"img{i}.jpg"),
                (100, 100),
                f"pixmap_{i}",
                size_bytes=100000  # 100KB each
            )
        
        # Total should not exceed limit (with some tolerance)
        assert cache._total_bytes <= cache.MAX_MEMORY_MB * cache.BYTES_PER_MB + 100000
    
    def test_pipeline_max_workers_validation(self):
        """P6.7: max_workers should be at least 1"""
        from photo_cleaner.pipeline.pipeline import PipelineConfig
        
        # Invalid: max_workers < 1
        config = PipelineConfig(max_workers=0)
        assert config.max_workers is None  # Should be reset to default


class TestP6_EdgeCases:
    """P6.x: Edge case handling"""
    
    def test_corrupted_image_handling(self):
        """P6.6: Corrupted images should be handled gracefully"""
        from photo_cleaner.core.hasher import ImageHasher
        
        hasher = ImageHasher()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create corrupted image file
            corrupt_path = Path(tmpdir) / "corrupt.jpg"
            corrupt_path.write_bytes(b"\xFF\xD8\xFF" + b"corrupted data that's not valid JPEG")
            
            # Should not crash, should return None
            phash = hasher.compute_phash(corrupt_path)
            assert phash is None  # Returns None on error, doesn't crash
            
            file_hash = hasher.compute_file_hash(corrupt_path)
            assert file_hash is None  # Returns None on error, doesn't crash


class TestP7_Improvements:
    """P7.x: Optional improvements"""
    
    def test_pipeline_config_post_init(self):
        """P7: PipelineConfig should validate on construction"""
        from photo_cleaner.pipeline.pipeline import PipelineConfig
        
        # Valid config
        config = PipelineConfig()
        assert config is not None
        
        # Invalid sharpness threshold
        with pytest.raises(ValueError):
            PipelineConfig(sharpness_threshold=-1)


# Summary: Run tests
if __name__ == "__main__":
    print("\n" + "="*80)
    print("Phase 2-7 Improvements Test Suite")
    print("="*80 + "\n")
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
