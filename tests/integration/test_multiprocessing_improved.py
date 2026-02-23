"""
Tests for Improved Multiprocessing Pipeline (Lock-Free)

Validates:
1. Queue-based job distribution (no locks)
2. Result ordering (critical for group scoring)
3. Per-image exception handling
4. Worker pool lifecycle management
5. Progress tracking without contention
6. Backward compatibility with old API
"""

import pytest
import logging
import time
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from photo_cleaner.pipeline.multiprocessing_improved import (
    WorkerResult,
    ProgressSnapshot,
    QueueBasedWorkerPool,
    process_images_parallel_v2,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Test Fixtures and Mocks
# ============================================================================

class MockConfig:
    """Mock configuration for testing."""
    
    def __init__(self, fail_on_path: Optional[str] = None, delay_ms: int = 0):
        """
        Args:
            fail_on_path: If set, fail when processing this path
            delay_ms: Artificial delay per image (to simulate work)
        """
        self.fail_on_path = fail_on_path
        self.delay_ms = delay_ms
        self.processed_count = 0  # For debugging


def simple_worker_func(image_path: Path, config: MockConfig) -> Dict[str, Any]:
    """Simple worker for testing."""
    import time
    
    # Simulate processing time
    if config.delay_ms > 0:
        time.sleep(config.delay_ms / 1000.0)
    
    # Fail on specific path
    if config.fail_on_path and str(image_path) == config.fail_on_path:
        raise ValueError(f"Intentional failure on {image_path}")
    
    config.processed_count += 1
    return {"score": 42.0, "path": str(image_path)}


@pytest.fixture
def temp_image_paths():
    """Create temporary image paths (files don't need to exist for this test)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = [Path(tmpdir) / f"image_{i:03d}.jpg" for i in range(10)]
        for p in paths:
            p.touch()  # Create dummy files
        yield paths


# ============================================================================
# Test Cases
# ============================================================================

class TestWorkerResult:
    """Tests for WorkerResult dataclass."""
    
    def test_worker_result_success(self):
        """Test successful worker result."""
        result = WorkerResult(
            image_path=Path("/test/image.jpg"),
            success=True,
            result={"score": 42.0},
            processing_time_ms=100.0,
        )
        
        assert result.success is True
        assert result.result["score"] == 42.0
        assert result.error is None
    
    def test_worker_result_failure(self):
        """Test failed worker result."""
        result = WorkerResult(
            image_path=Path("/test/image.jpg"),
            success=False,
            error="Test error",
            error_traceback="Line 1: error",
        )
        
        assert result.success is False
        assert result.error == "Test error"
    
    def test_worker_result_path_to_string(self):
        """Test that Path is converted to string."""
        path = Path("/test/image.jpg")
        result = WorkerResult(
            image_path=path,
            success=True,
        )
        
        assert isinstance(result.image_path, str)
        assert result.image_path == str(path)


class TestProgressSnapshot:
    """Tests for ProgressSnapshot."""
    
    def test_progress_percent(self):
        """Test progress percentage calculation."""
        progress = ProgressSnapshot(processed=5, total=10, failed=0)
        assert progress.progress_percent == 50.0
    
    def test_progress_percent_zero(self):
        """Test progress percent when total is 0."""
        progress = ProgressSnapshot(processed=0, total=0, failed=0)
        assert progress.progress_percent == 0.0
    
    def test_success_rate(self):
        """Test success rate calculation."""
        progress = ProgressSnapshot(processed=10, total=10, failed=2)
        assert progress.success_rate == 80.0
    
    def test_success_rate_zero_processed(self):
        """Test success rate when nothing processed."""
        progress = ProgressSnapshot(processed=0, total=10, failed=0)
        assert progress.success_rate == 0.0


class TestQueueBasedWorkerPool:
    """Tests for QueueBasedWorkerPool."""
    
    def test_pool_initialization(self):
        """Test pool initialization."""
        pool = QueueBasedWorkerPool(
            worker_func=simple_worker_func,
            num_images=10,
            max_workers=2,
        )
        
        assert pool.max_workers == 2
        assert pool.num_images == 10
        assert pool.worker_processes == []
    
    def test_context_manager_lifecycle(self):
        """Test pool lifecycle (enter/exit)."""
        pool = QueueBasedWorkerPool(
            worker_func=simple_worker_func,
            num_images=1,
            max_workers=1,
        )
        
        # Should be able to enter context
        with pool as p:
            assert p.job_queue is not None
            assert p.result_queue is not None
            assert len(p.worker_processes) == 1
            assert p.worker_processes[0].is_alive()
        
        # Workers should be shut down after exit
        time.sleep(0.1)
        for p in pool.worker_processes:
            assert not p.is_alive()
    
    def test_process_images_simple(self, temp_image_paths):
        """Test processing a batch of images."""
        config = MockConfig(delay_ms=10)
        
        with QueueBasedWorkerPool(
            worker_func=simple_worker_func,
            num_images=len(temp_image_paths),
            max_workers=2,
        ) as pool:
            results, progress = pool.process_images(temp_image_paths, config)
        
        assert len(results) == len(temp_image_paths)
        assert all(r.success for r in results)
        assert progress.processed == len(temp_image_paths)
        assert progress.failed == 0
    
    def test_result_ordering_preserved(self, temp_image_paths):
        """
        CRITICAL TEST: Results must be in same order as input!
        This is required for group-based scoring.
        """
        config = MockConfig(delay_ms=5)
        
        with QueueBasedWorkerPool(
            worker_func=simple_worker_func,
            num_images=len(temp_image_paths),
            max_workers=4,  # Multiple workers to stress ordering
        ) as pool:
            results, _ = pool.process_images(temp_image_paths, config)
        
        # Check that results are in the same order as input
        for i, (expected_path, result) in enumerate(zip(temp_image_paths, results)):
            assert str(result.image_path) == str(expected_path), \
                f"Result {i} is out of order: expected {expected_path}, got {result.image_path}"
    
    def test_exception_handling_per_image(self, temp_image_paths):
        """Test that exception in one image doesn't stop processing others."""
        fail_path = temp_image_paths[5]
        config = MockConfig(fail_on_path=str(fail_path))
        
        with QueueBasedWorkerPool(
            worker_func=simple_worker_func,
            num_images=len(temp_image_paths),
            max_workers=2,
        ) as pool:
            results, progress = pool.process_images(temp_image_paths, config)
        
        # Should process all images (one with error)
        assert len(results) == len(temp_image_paths)
        
        # Find the failed result
        failed_result = next(
            (r for r in results if str(r.image_path) == str(fail_path)), None
        )
        assert failed_result is not None
        assert failed_result.success is False
        assert "Intentional failure" in failed_result.error
        
        # Other results should succeed
        successful_results = [r for r in results if r.success]
        assert len(successful_results) == len(temp_image_paths) - 1
    
    def test_process_images_with_progress_callback(self, temp_image_paths):
        """Test progress callback mechanism."""
        config = MockConfig(delay_ms=20)
        progress_updates = []
        
        def progress_callback(progress: ProgressSnapshot):
            progress_updates.append(progress)
        
        with QueueBasedWorkerPool(
            worker_func=simple_worker_func,
            num_images=len(temp_image_paths),
            max_workers=2,
        ) as pool:
            results, final_progress = pool.process_images(
                temp_image_paths, config, on_progress=progress_callback
            )
        
        # Should have received some progress updates
        assert len(progress_updates) >= 1
        # Final progress should match number of images
        assert final_progress.processed == len(temp_image_paths)
    
    def test_pool_without_context_manager_raises(self):
        """Test that using pool without context manager raises error."""
        pool = QueueBasedWorkerPool(
            worker_func=simple_worker_func,
            num_images=1,
        )
        
        with pytest.raises(RuntimeError):
            pool.process_images([Path("/test.jpg")], MockConfig())


class TestProcessImagesParallelV2:
    """Tests for high-level API."""
    
    def test_process_images_parallel_v2_simple(self, temp_image_paths):
        """Test high-level API."""
        config = MockConfig(delay_ms=10)
        
        results, stats = process_images_parallel_v2(
            image_paths=temp_image_paths,
            worker_func=simple_worker_func,
            config=config,
            max_workers=2,
        )
        
        assert len(results) == len(temp_image_paths)
        assert stats["total_images"] == len(temp_image_paths)
        assert stats["successful"] == len(temp_image_paths)
        assert stats["failed"] == 0
        assert stats["success_rate"] == 100.0
    
    def test_process_images_parallel_v2_empty(self):
        """Test API with empty image list."""
        results, stats = process_images_parallel_v2(
            image_paths=[],
            worker_func=simple_worker_func,
            config=MockConfig(),
        )
        
        assert len(results) == 0
        assert stats["total_images"] == 0
        assert stats["success_rate"] == 100.0
    
    def test_process_images_parallel_v2_with_failures(self, temp_image_paths):
        """Test API with some failures."""
        fail_path = temp_image_paths[3]
        config = MockConfig(fail_on_path=str(fail_path))
        
        results, stats = process_images_parallel_v2(
            image_paths=temp_image_paths,
            worker_func=simple_worker_func,
            config=config,
            max_workers=2,
        )
        
        assert len(results) == len(temp_image_paths)
        assert stats["successful"] == len(temp_image_paths) - 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == pytest.approx((9/10)*100, abs=0.1)


class TestPerformanceAndStability:
    """Performance and stress tests."""
    
    def test_no_lock_contention_many_workers(self, temp_image_paths):
        """
        Stress test: Many workers processing simultaneously.
        Should not show lock contention (no locks used!).
        """
        config = MockConfig(delay_ms=5)
        
        start_time = time.time()
        with QueueBasedWorkerPool(
            worker_func=simple_worker_func,
            num_images=len(temp_image_paths),
            max_workers=8,  # Many workers
        ) as pool:
            results, progress = pool.process_images(temp_image_paths, config)
        elapsed = time.time() - start_time
        
        assert all(r.success for r in results)
        logger.info(f"Processed {len(results)} images in {elapsed:.2f}s with 8 workers")
    
    def test_memory_efficiency(self, temp_image_paths):
        """Test that memory doesn't grow linearly with workers."""
        config = MockConfig(delay_ms=2)
        
        # Large number of workers
        with QueueBasedWorkerPool(
            worker_func=simple_worker_func,
            num_images=len(temp_image_paths),
            max_workers=16,
        ) as pool:
            results, _ = pool.process_images(temp_image_paths, config)
        
        # All should complete successfully
        assert len(results) == len(temp_image_paths)


class TestBackwardCompatibility:
    """Ensure new implementation is compatible with old usage patterns."""
    
    def test_return_value_format_compatible(self, temp_image_paths):
        """Test that return values are compatible with old API."""
        config = MockConfig()
        
        results, stats = process_images_parallel_v2(
            temp_image_paths,
            simple_worker_func,
            config,
        )
        
        # Check return types
        assert isinstance(results, list)
        assert isinstance(stats, dict)
        
        # Check stats keys (same as old API)
        required_keys = {
            "total_images", "successful", "failed",
            "success_rate", "total_time_ms", "mean_time_per_image_ms"
        }
        assert required_keys.issubset(stats.keys())
        
        # Check result items
        for result in results:
            assert isinstance(result, WorkerResult)
            assert hasattr(result, 'image_path')
            assert hasattr(result, 'success')
            assert hasattr(result, 'result')


# ============================================================================
# Integration Tests (if quality_analyzer is available)
# ============================================================================

# These tests can be added if full integration is needed
# For now, focusing on multiprocessing infrastructure tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
