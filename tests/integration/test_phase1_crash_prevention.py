#!/usr/bin/env python3
"""
Phase 1 Crash-Prevention Tests

Tests für alle P1.x Fixes:
- P1.1: Worker process null-checks
- P1.2: Quality analyzer exception handling
- P1.3: Cache DB error fallback
- P1.4: Connection close safety
- P1.6: Transaction rollback
- P1.7: UI init crash handling
- P1.9: Export file-lock detection
- P1.10: License load safety
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import json


class TestP1_WorkerProcessNullChecks:
    """P1.1: Worker process defensive null-checks"""
    
    def test_worker_with_none_config(self):
        """Worker should return error dict, not crash"""
        from photo_cleaner.pipeline.worker_process import analyze_image_worker
        
        img_path = Path("dummy.jpg")
        result = analyze_image_worker(img_path, config=None)
        
        assert result['success'] is False
        assert result['error'] == 'Configuration error: config is None'
        assert result['disqualified'] is True
    
    def test_worker_with_missing_quality_analyzer(self):
        """Worker should handle missing quality_analyzer"""
        from photo_cleaner.pipeline.worker_process import analyze_image_worker
        
        img_path = Path("dummy.jpg")
        bad_config = Mock(spec=[])  # Empty spec - no quality_analyzer
        
        result = analyze_image_worker(img_path, config=bad_config)
        
        assert result['success'] is False
        assert 'quality_analyzer' in result['error']
        assert result['disqualified'] is True


class TestP1_CacheErrorFallback:
    """P1.3: Cache DB corruption doesn't break pipeline"""
    
    def test_cache_lookup_with_corrupted_db(self):
        """Cache lookup should return None on DB error, not crash"""
        from photo_cleaner.cache.image_cache_manager import ImageCacheManager
        
        # Create mock corrupted connection
        corrupted_conn = Mock(spec=sqlite3.Connection)
        corrupted_conn.cursor.side_effect = sqlite3.DatabaseError("Database corrupted")
        
        cache_mgr = ImageCacheManager.__new__(ImageCacheManager)
        cache_mgr.conn = corrupted_conn
        cache_mgr.stats = Mock()
        cache_mgr.stats.cache_misses = 0  # Initialize with actual value
        cache_mgr.PIPELINE_VERSION = 1
        
        # Should return None, not crash
        result = cache_mgr.lookup(Path("test.jpg"))
        
        assert result is None


class TestP1_LicenseLoadSafety:
    """P1.10: License load should never crash app"""
    
    def test_license_manager_with_corrupted_file(self):
        """License manager should fallback to FREE on corrupted file"""
        from photo_cleaner.license import LicenseManager, LicenseType
        from photo_cleaner.config import AppConfig
        
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)
            license_file = app_dir / "photo_cleaner.license"
            
            # Write corrupted license file
            with open(license_file, "w") as f:
                f.write("CORRUPTED_INVALID_LICENSE_DATA_{{{{")
            
            # Should not crash, should fallback to FREE
            # Isolate user data dir to avoid picking up real activation markers
            old_user_dir = AppConfig._user_data_dir
            try:
                AppConfig.set_user_data_dir(app_dir)
                lic_mgr = LicenseManager(app_dir)
            finally:
                AppConfig._user_data_dir = old_user_dir
            
            assert lic_mgr.license_info is not None
            assert lic_mgr.license_info.license_type == LicenseType.FREE
    
    def test_license_manager_with_empty_file(self):
        """License manager handles empty license file"""
        from photo_cleaner.license import LicenseManager, LicenseType
        from photo_cleaner.config import AppConfig
        
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)
            license_file = app_dir / "photo_cleaner.license"
            
            # Write empty license file
            with open(license_file, "w") as f:
                f.write("")
            
            old_user_dir = AppConfig._user_data_dir
            try:
                AppConfig.set_user_data_dir(app_dir)
                lic_mgr = LicenseManager(app_dir)
            finally:
                AppConfig._user_data_dir = old_user_dir
            assert lic_mgr.license_info.license_type == LicenseType.FREE
    
    def test_license_manager_without_file(self):
        """License manager handles missing license file gracefully"""
        from photo_cleaner.license import LicenseManager, LicenseType
        from photo_cleaner.config import AppConfig
        
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)
            # No license file created
            old_user_dir = AppConfig._user_data_dir
            try:
                AppConfig.set_user_data_dir(app_dir)
                lic_mgr = LicenseManager(app_dir)
            finally:
                AppConfig._user_data_dir = old_user_dir
            assert lic_mgr.license_info is not None
            assert lic_mgr.license_info.license_type == LicenseType.FREE


class TestP1_RepositoryTransactionRollback:
    """P1.6: DB operations should rollback on error"""
    
    def test_mark_deleted_with_error_rolls_back(self):
        """mark_deleted should rollback on error"""
        from photo_cleaner.repositories.file_repository import FileRepository
        from photo_cleaner.models.status import FileStatus
        
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_conn.execute.side_effect = sqlite3.IntegrityError("PK constraint")
        mock_conn.rollback = Mock()
        
        repo = FileRepository(mock_conn)
        
        # Should raise but rollback should be called
        with pytest.raises(sqlite3.IntegrityError):
            repo.mark_deleted([1, 2, 3])
        
        # Verify rollback was called
        mock_conn.rollback.assert_called()


class TestP1_ExporterFileLockDetection:
    """P1.9: Exporter should detect locked files"""
    
    def test_exporter_handles_locked_file(self):
        """Exporter should handle permission errors for locked files"""
        from photo_cleaner.exporter import Exporter
        
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = Exporter(Path(tmpdir))
            
            # Mock a locked file
            locked_file = Path(tmpdir) / "locked.jpg"
            
            # Patch open() to raise PermissionError
            with patch("builtins.open", side_effect=PermissionError("File is locked")):
                success, target, error = exporter.export_file(locked_file)
                
                assert success is False
                assert error is not None
                assert "locked" in error.lower() or "permission" in error.lower()


class TestP1_QualityAnalyzerExceptionHandling:
    """P1.2: Quality analyzer should handle cv2 errors gracefully"""
    
    def test_quality_analyzer_with_corrupt_image(self):
        """Quality analyzer should not crash on corrupt image"""
        from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer, FaceQuality
        import numpy as np
        
        qa = QualityAnalyzer()
        
        # Create invalid image array
        bad_image = np.array([])  # Empty array
        
        # Should not crash, should return neutral result
        try:
            result = qa._analyze_faces_haar(bad_image)
            assert isinstance(result, FaceQuality)
        except Exception as e:
            # If exception occurs, it should be caught higher up
            pytest.fail(f"QualityAnalyzer should handle bad images: {e}")


# Summary: Run tests
if __name__ == "__main__":
    print("\n" + "="*80)
    print("Phase 1 Crash-Prevention Test Suite")
    print("="*80 + "\n")
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "="*80)
    print("Tests Complete!")
    print("="*80 + "\n")
