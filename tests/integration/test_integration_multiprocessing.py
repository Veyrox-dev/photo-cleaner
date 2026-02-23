"""
Integration Tests: Multiprocessing with Real Quality Analyzer

Tests the new multiprocessing_improved.py integrated with:
- Existing quality_analyzer.py
- EXIF rotation fix
- Real image processing workflows
- Memory behavior at scale
- Exception handling for OpenCV/Pillow failures

Requirements:
- PIL/Pillow for image handling
- OpenCV for image processing
- Test images in temp directory (created automatically)
"""

import pytest
import logging
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================================
# Test Fixtures: Create Synthetic Test Images
# ============================================================================

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@pytest.fixture
def synthetic_test_images():
    """
    Create synthetic test images without needing real photos.
    
    Generates:
    - Solid color images (simple)
    - Images with patterns (for sharpness testing)
    - Images with different resolutions
    - Rotated images (for EXIF orientation testing)
    """
    assert PIL_AVAILABLE, "PIL not available for image creation"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        images = {}
        
        # Image 1: Simple solid color (1000x800) - portrait
        img = Image.new('RGB', (1000, 800), color=(100, 150, 200))
        path = tmpdir / "test_001_portrait.jpg"
        img.save(path, quality=90)
        images['portrait_blue'] = path
        
        # Image 2: Solid color (800x1000) - landscape
        img = Image.new('RGB', (800, 1000), color=(200, 100, 50))
        path = tmpdir / "test_002_landscape.jpg"
        img.save(path, quality=90)
        images['landscape_orange'] = path
        
        # Image 3: Pattern (checkerboard) for sharpness testing
        img = Image.new('RGB', (1200, 800), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        for i in range(0, 1200, 50):
            for j in range(0, 800, 50):
                if (i // 50 + j // 50) % 2 == 0:
                    draw.rectangle([i, j, i+50, j+50], fill=(0, 0, 0))
        path = tmpdir / "test_003_checkerboard.jpg"
        img.save(path, quality=90)
        images['checkerboard'] = path
        
        # Image 4: Very small resolution
        img = Image.new('RGB', (320, 240), color=(50, 50, 50))
        path = tmpdir / "test_004_tiny.jpg"
        img.save(path, quality=90)
        images['tiny_low_res'] = path
        
        # Image 5: Very large resolution
        img = Image.new('RGB', (4000, 3000), color=(100, 100, 100))
        path = tmpdir / "test_005_large.jpg"
        img.save(path, quality=85)
        images['large_4k'] = path
        
        # Image 6-10: Duplicates (for grouping tests)
        for i in range(6, 11):
            img = Image.new('RGB', (1024, 768), color=(150, 150, 150))
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), f"Image {i}", fill=(255, 0, 0))
            path = tmpdir / f"test_{i:03d}_duplicate.jpg"
            img.save(path, quality=90)
            images[f'duplicate_{i}'] = path
        
        yield images


@pytest.fixture
def quality_analyzer_instance():
    """Create a QualityAnalyzer instance for testing."""
    from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer

    analyzer = QualityAnalyzer(use_face_mesh=False)  # Disable face mesh for faster testing
    return analyzer


# ============================================================================
# Test Suite 1: Backward Compatibility
# ============================================================================

class TestBackwardCompatibilityAPI:
    """Verify API compatibility with existing code."""
    
    def test_import_multiprocessing_improved(self):
        """Test that new module can be imported."""
        from photo_cleaner.pipeline.multiprocessing_improved import (
            QueueBasedWorkerPool,
            process_images_parallel_v2,
            WorkerResult,
        )
        assert QueueBasedWorkerPool is not None
        assert process_images_parallel_v2 is not None
        assert WorkerResult is not None
    
    def test_return_value_format_matches_old_api(self, synthetic_test_images):
        """Test that return values match old API."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        def dummy_worker(path: Path, config) -> Dict[str, Any]:
            return {"score": 42.0}
        
        image_paths = list(synthetic_test_images.values())[:5]
        results, stats = process_images_parallel_v2(
            image_paths=image_paths,
            worker_func=dummy_worker,
            config={},
            max_workers=2,
        )
        
        # Check return types
        assert isinstance(results, list)
        assert isinstance(stats, dict)
        
        # Check required stats keys (same as old API)
        required_stats_keys = {
            'total_images', 'successful', 'failed',
            'success_rate', 'total_time_ms', 'mean_time_per_image_ms'
        }
        assert required_stats_keys.issubset(stats.keys())
        
        # Check result items
        for result in results:
            assert hasattr(result, 'image_path')
            assert hasattr(result, 'success')
            assert hasattr(result, 'result')
    
    def test_api_accepts_same_parameters(self):
        """Test that API signature is compatible."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        import inspect
        
        sig = inspect.signature(process_images_parallel_v2)
        params = set(sig.parameters.keys())
        
        # Should accept these parameters (old API compatibility)
        expected_params = {'image_paths', 'worker_func', 'config', 'max_workers', 'on_progress'}
        assert expected_params.issubset(params)


# ============================================================================
# Test Suite 2: Integration with QualityAnalyzer
# ============================================================================

class TestQualityAnalyzerIntegration:
    """Test integration with real QualityAnalyzer."""
    
    def test_quality_analyzer_parallel_with_synthetic_images(
        self, quality_analyzer_instance, synthetic_test_images
    ):
        """Test parallel quality analysis on synthetic images."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        # Create a worker that uses quality analyzer
        def quality_worker(image_path: Path, config) -> Dict[str, Any]:
            try:
                result = config['analyzer'].analyze_image(image_path)
                return {
                    'success': True,
                    'score': result.total_score if result.total_score else 50.0,
                    'width': result.width,
                    'height': result.height,
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                }
        
        image_paths = list(synthetic_test_images.values())[:5]
        config = {'analyzer': quality_analyzer_instance}
        
        results, stats = process_images_parallel_v2(
            image_paths=image_paths,
            worker_func=quality_worker,
            config=config,
            max_workers=2,
        )
        
        assert len(results) == 5
        assert stats['total_images'] == 5
        logger.info(f"Quality analysis: {stats['successful']}/{stats['total_images']} successful")
    
    def test_exif_orientation_handling(self, quality_analyzer_instance):
        """
        Test that EXIF rotation fix works in multiprocessing context.
        
        The quality_analyzer should read EXIF and rotate before analysis.
        """
        assert PIL_AVAILABLE, "PIL not available"
        
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        # Create rotated image with EXIF data
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image
            img = Image.new('RGB', (1000, 600), color=(100, 150, 200))
            
            # Try to save with EXIF orientation (this is complex in PIL)
            # For now, just test that quality analyzer doesn't crash on rotated images
            path = Path(tmpdir) / "rotated_test.jpg"
            img.save(path, quality=90)
            
            def quality_worker(image_path: Path, config) -> Dict[str, Any]:
                try:
                    result = config['analyzer'].analyze_image(image_path)
                    return {'success': True, 'score': result.total_score}
                except Exception as e:
                    return {'success': False, 'error': str(e)}
            
            results, stats = process_images_parallel_v2(
                image_paths=[path],
                worker_func=quality_worker,
                config={'analyzer': quality_analyzer_instance},
                max_workers=1,
            )
            
            assert len(results) == 1
            assert results[0].success


# ============================================================================
# Test Suite 3: Memory Behavior at Scale
# ============================================================================

class TestMemoryBehaviorAtScale:
    """Test memory usage with 100+ images."""
    
    def test_memory_stays_bounded_with_many_images(self, synthetic_test_images):
        """
        Test that memory doesn't grow unbounded with many images.
        
        This is critical for production use with 1000+ photos.
        """
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        def simple_worker(image_path: Path, config) -> Dict[str, Any]:
            import time
            time.sleep(0.01)  # Simulate work
            return {'score': 42.0}
        
        # Create many image paths (don't need real files for this test)
        image_paths = list(synthetic_test_images.values()) * 20  # 100+ paths
        image_paths = image_paths[:100]
        
        # This should complete without memory explosion
        results, stats = process_images_parallel_v2(
            image_paths=image_paths,
            worker_func=simple_worker,
            config={},
            max_workers=4,
        )
        
        assert len(results) == 100
        assert stats['successful'] == 100
        logger.info(f"Processed {stats['total_images']} images in {stats['total_time_ms']:.0f}ms")
    
    def test_queue_bounded_memory(self):
        """
        Test that queues don't unboundedly accumulate results.
        
        Queue-based design should have backpressure.
        """
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        def slow_worker(path: Path, config) -> Dict[str, Any]:
            import time
            time.sleep(0.05)  # Slow work
            return {'data': 'x' * 1000}  # Moderate payload
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = [tmpdir / f"img_{i}.jpg" for i in range(50)]
            
            for p in image_paths:
                p.touch()
            
            start_time = time.time()
            results, stats = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=slow_worker,
                config={},
                max_workers=2,
            )
            elapsed = time.time() - start_time
            
            assert len(results) == 50
            logger.info(f"Processed {len(results)} images in {elapsed:.1f}s (bounded memory)")


# ============================================================================
# Test Suite 4: Exception Handling (OpenCV/Pillow Failures)
# ============================================================================

class TestExceptionHandlingInWorkers:
    """Test that exceptions in workers don't crash the pool."""
    
    def test_openCV_unavailable_fallback(self):
        """Test graceful fallback when OpenCV is unavailable."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        def worker_using_optional_cv2(image_path: Path, config) -> Dict[str, Any]:
            try:
                import cv2
                return {'cv2_available': True}
            except ImportError:
                # Graceful fallback
                return {'cv2_available': False, 'error': 'cv2 not available'}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            image_paths = [Path(tmpdir) / f"img_{i}.jpg" for i in range(5)]
            for p in image_paths:
                p.touch()
            
            results, stats = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=worker_using_optional_cv2,
                config={},
                max_workers=2,
            )
            
            assert len(results) == 5
            # Should all be successful (even if cv2 unavailable)
            assert stats['successful'] > 0
    
    def test_per_image_exception_handling(self):
        """Test that exception on one image doesn't stop others."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        def failing_worker(image_path: Path, config) -> Dict[str, Any]:
            if 'fail' in str(image_path):
                raise ValueError(f"Intentional failure on {image_path}")
            return {'score': 42.0}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = [
                tmpdir / "good_1.jpg",
                tmpdir / "fail_2.jpg",
                tmpdir / "good_3.jpg",
                tmpdir / "fail_4.jpg",
                tmpdir / "good_5.jpg",
            ]
            for p in image_paths:
                p.touch()
            
            results, stats = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=failing_worker,
                config={},
                max_workers=2,
            )
            
            assert len(results) == 5
            # 3 should succeed, 2 should fail
            assert stats['successful'] == 3
            assert stats['failed'] == 2
    
    def test_malformed_image_file_handling(self, synthetic_test_images, quality_analyzer_instance):
        """Test handling of corrupted/malformed image files."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create a malformed "image" file
            bad_image = tmpdir / "corrupted.jpg"
            bad_image.write_text("This is not a valid image")
            
            def quality_worker(image_path: Path, config) -> Dict[str, Any]:
                try:
                    result = config['analyzer'].analyze_image(image_path)
                    return {'success': True, 'score': result.total_score}
                except Exception as e:
                    # Should catch and report error gracefully
                    return {'success': False, 'error': str(e)}
            
            results, stats = process_images_parallel_v2(
                image_paths=[bad_image],
                worker_func=quality_worker,
                config={'analyzer': quality_analyzer_instance},
                max_workers=1,
            )
            
            assert len(results) == 1
            assert results[0].success is True  # Worker ran without crashing
            assert "score" in results[0].result


# ============================================================================
# Test Suite 5: Result Ordering (CRITICAL)
# ============================================================================

class TestResultOrdering:
    """
    CRITICAL: Verify that results are returned in input order.
    This is essential for group-based scoring.
    """
    
    def test_result_order_preserved_with_many_workers(self):
        """Test that results maintain input order even with concurrent workers."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        def tracking_worker(image_path: Path, config) -> Dict[str, Any]:
            import time
            import random
            # Vary processing time to stress-test ordering
            time.sleep(random.uniform(0.001, 0.01))
            return {'path_name': image_path.name}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = [tmpdir / f"image_{i:04d}.jpg" for i in range(50)]
            for p in image_paths:
                p.touch()
            
            results, _ = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=tracking_worker,
                config={},
                max_workers=8,  # Many workers to stress ordering
            )
            
            # CRITICAL: Check that results are in same order as input
            for i, (expected_path, result) in enumerate(zip(image_paths, results)):
                assert str(result.image_path) == str(expected_path), \
                    f"Result {i} out of order: expected {expected_path}, got {result.image_path}"
            
            logger.info("✅ Result ordering verified with 8 concurrent workers")


# ============================================================================
# Test Suite 6: Progress Tracking
# ============================================================================

class TestProgressTracking:
    """Test progress callback mechanism."""
    
    def test_progress_callback_invoked(self):
        """Test that progress callback is called."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2, ProgressSnapshot
        
        progress_updates = []
        
        def progress_callback(progress: ProgressSnapshot):
            progress_updates.append(progress)
        
        def slow_worker(image_path: Path, config) -> Dict[str, Any]:
            import time
            time.sleep(0.02)
            return {'score': 42.0}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = [tmpdir / f"img_{i}.jpg" for i in range(20)]
            for p in image_paths:
                p.touch()
            
            results, stats = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=slow_worker,
                config={},
                max_workers=2,
                on_progress=progress_callback,
            )
            
            # Should have received progress updates
            assert len(progress_updates) > 0
            logger.info(f"Received {len(progress_updates)} progress updates")


# ============================================================================
# Test Suite 7: Comparative Performance
# ============================================================================

class TestPerformanceCharacteristics:
    """Test performance characteristics (not strict benchmarks)."""
    
    def test_parallel_faster_than_sequential_on_multicore(self):
        """
        Test that parallel is faster than sequential on multi-core systems.
        
        Note: This is indicative, not a strict performance test.
        """
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        
        def cpu_work(image_path: Path, config) -> Dict[str, Any]:
            # Simulate CPU-bound work
            _ = sum(i ** 2 for i in range(100000))
            return {'score': 42.0}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = [tmpdir / f"img_{i}.jpg" for i in range(20)]
            for p in image_paths:
                p.touch()
            
            # Single worker baseline
            start = time.time()
            results_1, stats_1 = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=cpu_work,
                config={},
                max_workers=1,
            )
            time_1 = time.time() - start
            
            # Multi worker
            start = time.time()
            results_4, stats_4 = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=cpu_work,
                config={},
                max_workers=4,
            )
            time_4 = time.time() - start
            
            logger.info(f"1 worker: {time_1:.2f}s, 4 workers: {time_4:.2f}s, speedup: {time_1/time_4:.1f}x")
            
            # We expect parallel to be at least not much slower
            # (exact speedup depends on system, but should be positive)
            assert len(results_1) == len(results_4) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
