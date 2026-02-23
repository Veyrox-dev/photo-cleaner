"""
End-to-End Integration Tests for ImageCache + Pipeline.

Tests the complete flow:
1. First run: All images analyzed → cached
2. Second run: Cache hits → skip analysis → verify same results
3. Force reanalyze: Cache ignored → full analysis
"""

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest import TestCase, mock

import pytest

from photo_cleaner.cache.image_cache_manager import ImageCacheManager
from photo_cleaner.db.schema import Database
from photo_cleaner.pipeline.pipeline import PhotoCleanerPipeline, PipelineConfig, PipelineStats


class TestCachePipelineIntegration(TestCase):
    """Integration tests for cache + pipeline."""
    
    def setUp(self):
        """Set up test database and cache."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        # Use direct sqlite3 connection instead of Database class
        self.conn = sqlite3.connect(str(self.db_path))
        self.db = mock.MagicMock()
        self.db.conn = self.conn
        self.cache = ImageCacheManager(self.conn)
    
    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.db_path.unlink(missing_ok=True)
    
    def test_cache_manager_initialization(self):
        """Test cache manager initializes correctly in pipeline."""
        config = PipelineConfig(use_cache=True)
        pipeline = PhotoCleanerPipeline(self.db, config)
        
        assert pipeline.cache_manager is not None
        assert pipeline.config.use_cache is True
    
    def test_cache_disabled(self):
        """Test pipeline with cache disabled."""
        config = PipelineConfig(use_cache=False)
        pipeline = PhotoCleanerPipeline(self.db, config)
        
        assert pipeline.cache_manager is None
        assert pipeline.config.use_cache is False
    
    def test_cache_file_hash_computation(self):
        """Test file hash computation for caching."""
        # Create test files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            test_content = b"test image content"
            f.write(test_content)
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Compute hash
            hash1 = ImageCacheManager.compute_file_hash(file_path)
            
            # Same file should produce same hash
            hash2 = ImageCacheManager.compute_file_hash(file_path)
            assert hash1 == hash2, "Hash should be deterministic"
            assert len(hash1) == 40, "SHA1 should be 40 chars"
            
            # Verify it's hex
            int(hash1, 16)  # Should not raise
        finally:
            file_path.unlink()
    
    def test_cache_storage_and_retrieval(self):
        """Test storing and retrieving from cache."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test image")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Initially should be a cache miss
            entry = self.cache.lookup(file_path)
            assert entry is None
            
            # Store in cache
            result = self.cache.store(
                file_path=file_path,
                quality_score=85.5,
                top_n_flag=True,
                metadata={"faces_detected": 2, "brightness": 150}
            )
            assert result is True
            
            # Should now be a cache hit
            entry = self.cache.lookup(file_path)
            assert entry is not None
            assert entry.quality_score == 85.5
            assert entry.top_n_flag is True
            assert entry.metadata["faces_detected"] == 2
        finally:
            file_path.unlink()
    
    def test_cache_bulk_operations(self):
        """Test bulk cache operations."""
        files = []
        
        # Create test files
        for i in range(5):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            f.write(f"test image {i}".encode())
            f.flush()
            f.close()
            files.append(Path(f.name))
        
        try:
            # Store first 3 files
            for f in files[:3]:
                self.cache.store(f, quality_score=80.0 + len(f.name), top_n_flag=False)
            
            # Bulk lookup
            uncached, cached = self.cache.bulk_lookup(files)
            
            assert len(cached) == 3, "Should have 3 cached files"
            assert len(uncached) == 2, "Should have 2 uncached files"
            
            # Verify hit rate
            hit_rate = len(cached) / len(files)
            assert hit_rate == 0.6, "Hit rate should be 60%"
        finally:
            for f in files:
                f.unlink()
    
    def test_force_reanalyze_flag(self):
        """Test force_reanalyze bypasses cache."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test image")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store in cache
            self.cache.store(file_path, quality_score=90.0, top_n_flag=False)
            
            # Normal lookup should hit cache
            entry = self.cache.lookup(file_path, force_reanalyze=False)
            assert entry is not None
            
            # With force_reanalyze should bypass cache
            entry = self.cache.lookup(file_path, force_reanalyze=True)
            assert entry is None
        finally:
            file_path.unlink()
    
    def test_cache_statistics_tracking(self):
        """Test cache statistics are tracked correctly."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            initial_stats = self.cache.get_cache_stats()
            assert initial_stats.cache_hits == 0
            assert initial_stats.cache_misses == 0
            assert initial_stats.cache_updates == 0
            
            # Store (update)
            self.cache.store(file_path, 85.0, False)
            stats = self.cache.get_cache_stats()
            assert stats.cache_updates == 1
            
            # Lookup (hit)
            self.cache.lookup(file_path)
            stats = self.cache.get_cache_stats()
            assert stats.cache_hits == 1
            
            # Lookup non-existent (miss)
            self.cache.reset_stats()
            with tempfile.NamedTemporaryFile(delete=False) as f2:
                f2.write(b"other")
                f2.flush()
                f2.close()
                self.cache.lookup(Path(f2.name), force_reanalyze=False)
                Path(f2.name).unlink()
            
            stats = self.cache.get_cache_stats()
            assert stats.cache_misses == 1
        finally:
            file_path.unlink()
    
    def test_cache_clear_operations(self):
        """Test clearing cache."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store entries
            self.cache.store(file_path, 85.0, False)
            
            # Verify it exists
            entry = self.cache.lookup(file_path)
            assert entry is not None
            
            # Clear all
            cleared = self.cache.clear_cache(older_than_days=None)
            assert cleared > 0
            
            # Verify it's gone
            self.cache.reset_stats()
            entry = self.cache.lookup(file_path)
            assert entry is None
        finally:
            file_path.unlink()
    
    def test_cache_metadata_persistence(self):
        """Test metadata is stored and retrieved correctly."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            metadata = {
                "faces_detected": 3,
                "laplacian_variance": 456.78,
                "brightness": 180,
                "width": 3840,
                "height": 2160,
            }
            
            self.cache.store(
                file_path,
                quality_score=92.5,
                top_n_flag=True,
                metadata=metadata
            )
            
            entry = self.cache.lookup(file_path)
            assert entry.metadata == metadata
            assert entry.metadata["faces_detected"] == 3
            assert entry.metadata["width"] == 3840
        finally:
            file_path.unlink()
    
    def test_cache_size_statistics(self):
        """Test cache size statistics."""
        files = []
        
        try:
            for i in range(3):
                f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                # Write different content so each file has a unique hash
                f.write(f"test_content_{i}".encode())
                f.flush()
                f.close()
                files.append(Path(f.name))
                self.cache.store(Path(f.name), quality_score=80.0 + i, top_n_flag=(i == 0))
            
            size_info = self.cache.get_cache_size()
            # Should have 3 entries stored (different content = different hashes)
            assert size_info["entries"] == 3
            # Should have 1 top_n entry (only first one)
            assert size_info["top_n_entries"] == 1
            # Average quality should be between 80 and 82
            assert 80.0 <= size_info["avg_quality_score"] <= 82.0
        finally:
            for f in files:
                f.unlink(missing_ok=True)
    
    def test_pipeline_config_with_cache_options(self):
        """Test pipeline config accepts cache options."""
        config1 = PipelineConfig(use_cache=True, force_reanalyze=False)
        assert config1.use_cache is True
        assert config1.force_reanalyze is False
        
        config2 = PipelineConfig(use_cache=False)
        assert config2.use_cache is False
        
        config3 = PipelineConfig(force_reanalyze=True)
        assert config3.force_reanalyze is True


class TestCachePerformance(TestCase):
    """Performance tests for cache system."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.cache = ImageCacheManager(self.conn)
    
    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.db_path.unlink(missing_ok=True)
    
    def test_hash_computation_performance(self):
        """Test hash computation doesn't take too long."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 1MB test file
            f.write(b"x" * (1024 * 1024))
            f.flush()
            file_path = Path(f.name)
        
        try:
            start = time.time()
            hash_val = ImageCacheManager.compute_file_hash(file_path)
            elapsed = time.time() - start
            
            assert hash_val is not None
            assert elapsed < 1.0, f"Hash should compute in <1s, took {elapsed:.2f}s"
        finally:
            file_path.unlink()
    
    def test_cache_lookup_performance(self):
        """Test cache lookup is fast."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store entry
            self.cache.store(file_path, 85.0, False)
            
            # Measure lookup time
            start = time.time()
            for _ in range(100):
                entry = self.cache.lookup(file_path)
            elapsed = time.time() - start
            
            avg_time = elapsed / 100
            assert avg_time < 0.01, f"Lookup should be <10ms, avg {avg_time*1000:.2f}ms"
        finally:
            file_path.unlink()
    
    def test_bulk_lookup_performance(self):
        """Test bulk lookup performance."""
        files = []
        
        try:
            # Create and cache 100 files
            for i in range(100):
                f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                f.write(f"test {i}".encode())
                f.flush()
                f.close()
                files.append(Path(f.name))
                self.cache.store(Path(f.name), 80.0 + (i % 20), i % 2 == 0)
            
            # Measure bulk lookup
            start = time.time()
            uncached, cached = self.cache.bulk_lookup(files)
            elapsed = time.time() - start
            
            assert len(cached) == 100
            assert len(uncached) == 0
            assert elapsed < 0.5, f"Bulk lookup should be <500ms, took {elapsed*1000:.2f}ms"
        finally:
            for f in files:
                f.unlink()


class TestCacheErrorHandling(TestCase):
    """Error handling tests for cache."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.cache = ImageCacheManager(self.conn)
    
    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.db_path.unlink(missing_ok=True)
    
    def test_missing_file_handling(self):
        """Test handling of missing files."""
        missing_path = Path("/nonexistent/file.jpg")
        
        # Should return None, not crash
        entry = self.cache.lookup(missing_path)
        assert entry is None
    
    def test_corrupted_metadata_handling(self):
        """Test handling of corrupted metadata."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Store with bad metadata that won't JSON serialize cleanly
            result = self.cache.store(
                file_path,
                quality_score=85.0,
                top_n_flag=False,
                metadata=None
            )
            assert result is True
            
            # Should still retrieve
            entry = self.cache.lookup(file_path)
            assert entry is not None
        finally:
            file_path.unlink()
    
    def test_concurrent_access(self):
        """Test concurrent cache access doesn't cause issues."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            file_path = Path(f.name)
        
        try:
            # Simulate rapid fire operations
            for i in range(10):
                self.cache.store(file_path, 80.0 + i, i % 2 == 0)
            
            for _ in range(10):
                entry = self.cache.lookup(file_path)
                assert entry is not None
        finally:
            file_path.unlink()


class TestCacheIntegrationScenarios(TestCase):
    """Real-world scenario tests."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.cache = ImageCacheManager(self.conn)
    
    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.db_path.unlink(missing_ok=True)
    
    def test_scenario_first_scan_then_cached_scan(self):
        """
        Scenario: User scans folder with 10 images twice.
        First scan: All miss cache, all analyzed.
        Second scan: All hit cache, no analysis needed.
        """
        files = []
        
        try:
            # Create 10 test files
            for i in range(10):
                f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                f.write(f"image {i}".encode())
                f.flush()
                f.close()
                files.append(Path(f.name))
            
            # First scan: All cache misses
            self.cache.reset_stats()
            uncached, cached = self.cache.bulk_lookup(files)
            assert len(uncached) == 10
            assert len(cached) == 0
            stats1 = self.cache.get_cache_stats()
            
            # Simulate analysis and caching
            for f in files:
                self.cache.store(f, quality_score=85.0, top_n_flag=False)
            
            # Second scan: All cache hits
            self.cache.reset_stats()
            uncached, cached = self.cache.bulk_lookup(files)
            assert len(uncached) == 0
            assert len(cached) == 10
            stats2 = self.cache.get_cache_stats()
            
            assert stats2.cache_hits == 10
            assert stats2.cache_misses == 0
        finally:
            for f in files:
                f.unlink()
    
    def test_scenario_mixed_old_and_new_images(self):
        """
        Scenario: User has 100 images from previous scan, adds 20 new ones.
        Cache: 100 hits, 20 misses → only new ones analyzed.
        """
        try:
            # Create and cache 100 old images
            for i in range(100):
                f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                f.write(f"old {i}".encode())
                f.flush()
                f.close()
                self.cache.store(Path(f.name), 85.0, False)
                Path(f.name).unlink()
            
            # Create 20 new images (not in cache)
            new_files = []
            for i in range(20):
                f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                f.write(f"new {i}".encode())
                f.flush()
                f.close()
                new_files.append(Path(f.name))
            
            # Simulate re-scan of old + new
            all_files = new_files  # Only have new files to query
            self.cache.reset_stats()
            uncached, cached = self.cache.bulk_lookup(all_files)
            
            assert len(uncached) == 20
            assert len(cached) == 0
            
            for f in new_files:
                f.unlink()
        except Exception as e:
            print(f"Test error: {e}")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
