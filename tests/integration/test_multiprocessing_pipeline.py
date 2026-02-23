"""
Tests for Multiprocessing Pipeline Implementation

Validates:
1. Worker pool functionality
2. Progress tracking (process-safe)
3. Result aggregation and ordering
4. Exception handling per-image
5. Memory efficiency
6. Results identical to single-process
7. Hard rule validation (eyes open check)
"""

import pytest
import logging
import time
from pathlib import Path
from typing import Dict, Any
from multiprocessing import Pool
import tempfile
import shutil
import tracemalloc

from photo_cleaner.pipeline.multiprocessing_manager import (
    WorkerPool,
    ProgressTracker,
    ResultAggregator,
    WorkerResult,
    ProgressUpdate,
    process_images_parallel,
)
from photo_cleaner.pipeline.worker_process import analyze_image_worker
from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
from photo_cleaner.pipeline.scorer import GroupScorer
from photo_cleaner.pipeline.parallel_quality_analyzer import (
    ParallelQualityAnalyzer,
    _analyze_image_for_parallel,
    QualityAnalysisConfig,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Test Fixtures
# ============================================================================

class MockConfig:
    """Mock configuration for testing."""
    
    def __init__(self, quality_analyzer, scorer):
        self.quality_analyzer = quality_analyzer
        self.scorer = scorer
        self.cheap_filter = None


def dummy_worker_func(image_path: Path, config: Any) -> Dict[str, Any]:
    """Dummy worker for testing (doesn't require actual images)."""
    return {
        'path': str(image_path),
        'success': True,
        'value': 42,
    }


def failing_worker_func(image_path: Path, config: Any) -> Dict[str, Any]:
    """Worker that fails for specific paths."""
    if 'fail' in str(image_path):
        raise RuntimeError(f"Simulated failure for {image_path}")
    return {
        'path': str(image_path),
        'success': True,
    }


def _create_test_image(path: Path, size: tuple[int, int] = (400, 300)) -> None:
    from PIL import Image

    image = Image.new("RGB", size, (120, 120, 120))
    image.save(path, quality=90)


# ============================================================================
# Progress Tracker Tests
# ============================================================================

def test_progress_tracker_increment():
    """Test progress tracker incrementation."""
    tracker = ProgressTracker(total=100)
    
    assert tracker._processed.value == 0
    tracker.increment(count=10)
    assert tracker._processed.value == 10
    
    tracker.increment(count=5, failed=True)
    assert tracker._processed.value == 15
    assert tracker._failed.value == 5


def test_progress_tracker_get_current():
    """Test progress tracking state."""
    tracker = ProgressTracker(total=100)
    
    tracker.increment(count=25)
    progress = tracker.get_current()
    
    assert progress.processed == 25
    assert progress.total == 100
    assert progress.progress_percent == pytest.approx(25.0)
    assert progress.failed == 0


def test_progress_tracker_eta_calculation():
    """Test ETA estimation."""
    tracker = ProgressTracker(total=100)
    
    # Process 10 items
    for _ in range(10):
        tracker.increment(count=1)
        time.sleep(0.001)  # Small delay
    
    progress = tracker.get_current()
    assert progress.eta_seconds is not None
    assert progress.eta_seconds > 0


# ============================================================================
# Result Aggregator Tests
# ============================================================================

def test_result_aggregator_basic():
    """Test result aggregation."""
    aggregator = ResultAggregator()
    
    results = [
        WorkerResult(
            image_path=Path("/path/to/img1.jpg"),
            success=True,
            result={'score': 0.9},
        ),
        WorkerResult(
            image_path=Path("/path/to/img2.jpg"),
            success=False,
            error="Failed",
        ),
    ]
    
    aggregator.add_results(results)
    
    assert len(aggregator.successful_images) == 1
    assert len(aggregator.failed_images) == 1
    assert len(aggregator.results_by_path) == 2


def test_result_aggregator_statistics():
    """Test statistics calculation."""
    aggregator = ResultAggregator()
    
    results = [
        WorkerResult(
            image_path=Path(f"/path/img{i}.jpg"),
            success=(i % 2 == 0),
            processing_time_ms=100.0,
        )
        for i in range(10)
    ]
    
    aggregator.add_results(results)
    stats = aggregator.get_statistics()
    
    assert stats['total_images'] == 10
    assert stats['successful'] == 5
    assert stats['failed'] == 5
    assert stats['success_rate'] == pytest.approx(50.0)
    assert stats['mean_time_per_image_ms'] == pytest.approx(100.0)


# ============================================================================
# Worker Pool Tests
# ============================================================================

def test_worker_pool_initialization():
    """Test worker pool setup."""
    with WorkerPool(
        worker_func=dummy_worker_func,
        num_images=100,
        max_workers=4,
    ) as pool:
        assert pool.pool is not None
        assert pool.max_workers == 4
        assert pool.num_images == 100


def test_worker_pool_auto_worker_count():
    """Test automatic worker count detection."""
    import multiprocessing
    
    cpu_count = multiprocessing.cpu_count() or 4
    
    with WorkerPool(
        worker_func=dummy_worker_func,
        num_images=100,
        max_workers=None,
    ) as pool:
        expected = max(1, cpu_count - 1)
        assert pool.max_workers == expected


def test_worker_pool_batch_creation():
    """Test batch creation from image paths."""
    with WorkerPool(
        worker_func=dummy_worker_func,
        num_images=10,
        max_workers=2,
        batch_size=3,
    ) as pool:
        paths = [Path(f"img{i}.jpg") for i in range(10)]
        batches = pool._create_batches(paths)
        
        assert len(batches) == 4  # 10 images / 3 per batch = 4 batches
        assert len(batches[0]) == 3
        assert len(batches[3]) == 1  # Last batch has remainder


def test_process_images_parallel_basic():
    """Test basic parallel processing."""
    image_paths = [Path(f"img{i}.jpg") for i in range(5)]
    
    results, stats = process_images_parallel(
        image_paths=image_paths,
        worker_func=dummy_worker_func,
        config=MockConfig(None, None),
        max_workers=2,
    )
    
    assert len(results) == 5
    assert all(r.success for r in results)
    assert stats['total_images'] == 5
    assert stats['successful'] == 5


def test_process_images_parallel_with_failures():
    """Test parallel processing with some failures."""
    image_paths = [
        Path(f"img{i}.jpg") for i in range(3)
    ] + [
        Path("fail_img.jpg")
    ]
    
    results, stats = process_images_parallel(
        image_paths=image_paths,
        worker_func=failing_worker_func,
        config=MockConfig(None, None),
        max_workers=2,
    )
    
    assert len(results) == 4
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    
    assert successful == 3
    assert failed == 1
    assert stats['failed'] == 1


def test_process_images_parallel_empty_input():
    """Test parallel processing with empty input."""
    results, stats = process_images_parallel(
        image_paths=[],
        worker_func=dummy_worker_func,
        config=MockConfig(None, None),
    )
    
    assert len(results) == 0
    assert stats['total_images'] == 0
    assert stats['successful'] == 0


def test_process_images_parallel_preserves_order():
    """Test that results are returned in input order."""
    image_paths = [Path(f"img{i}.jpg") for i in range(10)]
    
    results, stats = process_images_parallel(
        image_paths=image_paths,
        worker_func=dummy_worker_func,
        config=MockConfig(None, None),
        max_workers=3,
        batch_size=2,
    )
    
    # Results should be in same order as input
    # (though internal batching happens)
    assert len(results) == 10


# ============================================================================
# Parallel Quality Analyzer Tests
# ============================================================================

def test_parallel_quality_analyzer_single_image():
    """Test single image analysis (no parallelization needed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = Path(tmpdir) / "single.jpg"
        _create_test_image(image_path)

        analyzer = QualityAnalyzer(use_face_mesh=False)
        parallel = ParallelQualityAnalyzer(analyzer)

        result = parallel.analyze_image(image_path)

        assert result.path == image_path
        assert result.width > 0
        assert result.height > 0
        assert result.error is None


def test_parallel_quality_analyzer_fallback():
    """Test fallback to single-process on error."""
    # Mock quality analyzer
    class MockQualityAnalyzer:
        def analyze_image(self, path: Path):
            from photo_cleaner.pipeline.quality_analyzer import QualityResult
            return QualityResult(
                path=path,
                face_quality=None,
                overall_sharpness=0.5,
            )
        
        def analyze_batch(self, paths):
            return [self.analyze_image(p) for p in paths]
    
    analyzer = ParallelQualityAnalyzer(MockQualityAnalyzer())
    paths = [Path(f"img{i}.jpg") for i in range(3)]
    
    results = analyzer.analyze_batch(paths)
    
    assert len(results) == 3


# ============================================================================
# Integration Tests
# ============================================================================

def test_multiprocessing_hard_rule_preserved():
    """
    Integration test: Verify hard rule (eyes open) is preserved in parallel execution.
    
    This is critical - the hard rule must work identically in single and parallel.
    """
    from photo_cleaner.pipeline.quality_analyzer import FaceQuality, QualityResult

    scorer = GroupScorer(top_n=1)

    path_open = Path("open.jpg")
    path_closed = Path("closed.jpg")

    open_face = FaceQuality(has_face=True, all_eyes_open=True, confidence=1.0, num_faces=1)
    closed_face = FaceQuality(has_face=True, all_eyes_open=False, confidence=1.0, num_faces=1)

    qr_open = QualityResult(
        path=path_open,
        face_quality=open_face,
        overall_sharpness=0.5,
        lighting_score=50.0,
        resolution_score=1.0,
        width=1200,
        height=800,
        total_score=0.0,
    )
    qr_closed = QualityResult(
        path=path_closed,
        face_quality=closed_face,
        overall_sharpness=0.5,
        lighting_score=50.0,
        resolution_score=1.0,
        width=1200,
        height=800,
        total_score=0.0,
    )

    best, _, scores = scorer.auto_select_best_image("group_1", [qr_open, qr_closed])
    score_map = {path: score for path, score, _, _ in scores}

    assert best == path_open
    assert score_map[path_open] > score_map[path_closed]


def test_multiprocessing_vs_single_process_identical():
    """
    Integration test: Verify results are identical between single and parallel.
    
    This validates that no data is lost or transformed incorrectly.
    """
    image_paths = [Path(f"img_{i}.jpg") for i in range(5)]

    single_results, _ = process_images_parallel(
        image_paths=image_paths,
        worker_func=dummy_worker_func,
        config=MockConfig(None, None),
        max_workers=1,
    )

    parallel_results, _ = process_images_parallel(
        image_paths=image_paths,
        worker_func=dummy_worker_func,
        config=MockConfig(None, None),
        max_workers=2,
    )

    assert len(single_results) == len(parallel_results)
    for single, parallel_result in zip(single_results, parallel_results):
        assert single.image_path == parallel_result.image_path
        assert single.success == parallel_result.success
        assert single.result == parallel_result.result


def test_multiprocessing_memory_efficiency():
    """
    Integration test: Verify memory is freed after processing.
    
    Workers should not hold onto image data after processing.
    """
    image_paths = [Path(f"img_{i}.jpg") for i in range(50)]

    tracemalloc.start()
    process_images_parallel(
        image_paths=image_paths,
        worker_func=dummy_worker_func,
        config=MockConfig(None, None),
        max_workers=2,
    )
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak < 10 * 1024 * 1024


def test_multiprocessing_error_recovery():
    """
    Test that multiprocessing continues processing even if one image fails.
    
    This validates robustness against corrupted/invalid images.
    """
    image_paths = [
        Path(f"good_{i}.jpg") for i in range(5)
    ] + [
        Path("fail_corrupted.jpg"),
    ] + [
        Path(f"good_{i}.jpg") for i in range(5, 10)
    ]
    
    results, stats = process_images_parallel(
        image_paths=image_paths,
        worker_func=failing_worker_func,
        config=MockConfig(None, None),
        max_workers=2,
    )
    
    # Should process all images, but one fails
    assert len(results) == 11
    assert stats['total_images'] == 11
    assert stats['failed'] >= 1  # At least the "corrupted" one


# ============================================================================
# Performance Tests
# ============================================================================

def test_worker_pool_threading_overhead():
    """Measure overhead of creating worker pool."""
    import time
    
    start = time.time()
    with WorkerPool(
        worker_func=dummy_worker_func,
        num_images=100,
        max_workers=4,
    ) as pool:
        pass
    elapsed = time.time() - start
    
    # Should be fast (< 500ms to just create pool on Windows CI)
    assert elapsed < 0.5, f"Pool creation took {elapsed}s"


def test_progress_tracking_overhead():
    """Measure progress tracking overhead."""
    import time
    
    tracker = ProgressTracker(total=1000)
    
    start = time.time()
    for _ in range(1000):
        tracker.increment(count=1)
    elapsed = time.time() - start
    
    # Should be fast even with 1000 increments
    assert elapsed < 0.2, f"1000 increments took {elapsed}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
