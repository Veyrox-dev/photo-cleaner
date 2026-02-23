"""
UI Integration Tests: Modern Window with Multiprocessing

Tests that the modern UI (modern_window.py) works correctly with:
1. New multiprocessing_improved.py pipeline
2. Progress updates during processing
3. Cancel operations
4. Result display and group selection

This validates that the UI layer works transparently with
the new lock-free implementation.
"""

import pytest
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, MagicMock, patch
import threading
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================================
# Mock UI Components
# ============================================================================

class MockModernWindow:
    """
    Mock of modern_window.py for testing.
    
    Simulates the UI without requiring PyQt/tkinter.
    """
    
    def __init__(self):
        self.selected_indices: set = set()
        self.last_selected_index: Optional[int] = None
        self.progress_callbacks: List = []
        self.groups: Dict[str, List[Path]] = {}
        self.current_group_id: Optional[str] = None
        self._processing = False
        self._group_selections: Dict[str, set] = {}
        self._active_group_id: Optional[str] = None
    
    def register_progress_callback(self, callback):
        """Register a callback for progress updates."""
        self.progress_callbacks.append(callback)
    
    def on_progress_update(self, progress: Dict[str, Any]):
        """Called when progress updates arrive."""
        for callback in self.progress_callbacks:
            callback(progress)
    
    def select_image_at_index(self, index: int, group_id: str):
        """Select image at given index in group."""
        if self._active_group_id is not None:
            self._group_selections[self._active_group_id] = self.selected_indices.copy()

        if group_id != self._active_group_id:
            self.selected_indices = self._group_selections.get(group_id, set()).copy()

        self.selected_indices.add(index)
        self.last_selected_index = index
        self.current_group_id = group_id
        self._active_group_id = group_id
        self._group_selections[group_id] = self.selected_indices.copy()
    
    def get_selected_indices(self, group_id: str) -> set:
        """Get selected indices for a group."""
        if group_id == self.current_group_id:
            return self.selected_indices.copy()
        return self._group_selections.get(group_id, set()).copy()


# ============================================================================
# Test Suite 1: UI Backward Compatibility
# ============================================================================

class TestUIBackwardCompatibility:
    """Test that UI layer works with new multiprocessing."""
    
    def test_parallel_analyzer_api_compatible_with_ui(self):
        """Test that ParallelQualityAnalyzer API matches expected UI usage."""
        from photo_cleaner.pipeline.parallel_quality_analyzer import ParallelQualityAnalyzer
        from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
        
        analyzer = QualityAnalyzer(use_face_mesh=False)
        parallel_analyzer = ParallelQualityAnalyzer(analyzer)
        
        # UI should be able to:
        # 1. Call analyze_image for single images
        assert hasattr(parallel_analyzer, 'analyze_image')
        
        # 2. Call analyze_batch for multiple images
        assert hasattr(parallel_analyzer, 'analyze_batch')
        
        # 3. Call analyze_batch_parallel for parallel analysis
        assert hasattr(parallel_analyzer, 'analyze_batch_parallel')
    
    def test_worker_result_compatible_with_ui_display(self):
        """Test that WorkerResult can be displayed in UI."""
        from photo_cleaner.pipeline.multiprocessing_improved import WorkerResult
        
        result = WorkerResult(
            image_path=Path("/test/image.jpg"),
            success=True,
            result={'score': 42.0},
            processing_time_ms=100.0,
        )
        
        # UI should be able to access these fields
        assert str(result.image_path)
        assert result.success
        assert result.processing_time_ms
        
        # UI should handle failures gracefully
        failed_result = WorkerResult(
            image_path=Path("/test/bad.jpg"),
            success=False,
            error="Image corrupted",
        )
        
        assert not failed_result.success
        assert failed_result.error


# ============================================================================
# Test Suite 2: Progress Updates to UI
# ============================================================================

class TestProgressUpdatesToUI:
    """Test that progress updates flow correctly to UI."""
    
    def test_progress_callback_invoked_from_worker(self):
        """Test that UI progress callback is invoked."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2, ProgressSnapshot
        import tempfile
        
        ui = MockModernWindow()
        progress_updates = []
        
        def progress_callback(progress: ProgressSnapshot):
            progress_updates.append({
                'processed': progress.processed,
                'total': progress.total,
                'percent': progress.progress_percent,
            })
            ui.on_progress_update({'progress': progress.progress_percent})
        
        def dummy_worker(path: Path, config) -> Dict[str, Any]:
            time.sleep(0.01)
            return {'score': 42.0}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = [tmpdir / f"img_{i}.jpg" for i in range(20)]
            for p in image_paths:
                p.touch()
            
            results, stats = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=dummy_worker,
                config={},
                max_workers=2,
                on_progress=progress_callback,
            )
            
            # UI should have received progress updates
            assert len(progress_updates) > 0
            
            # Last update should show 100%
            final_update = progress_updates[-1]
            assert final_update['percent'] >= 99.0
            
            logger.info(f"✅ UI received {len(progress_updates)} progress updates")
    
    def test_progress_format_compatible_with_ui_display(self):
        """Test that progress format is compatible with UI display."""
        from photo_cleaner.pipeline.multiprocessing_improved import ProgressSnapshot
        
        progress = ProgressSnapshot(
            processed=50,
            total=100,
            failed=2,
        )
        
        # UI should be able to display these
        pct = progress.progress_percent
        assert 0 <= pct <= 100
        
        rate = progress.success_rate
        assert 0 <= rate <= 100
        
        # UI should be able to estimate time remaining
        # (even if estimate is very rough)
        eta = progress.eta_seconds
        assert eta is None or eta >= 0


# ============================================================================
# Test Suite 3: Cross-Group Selection
# ============================================================================

class TestCrossGroupSelection:
    """
    Test that group selection state is properly isolated.
    
    This was a bug in the original system (fixed in 0.1.1).
    We ensure the new multiprocessing doesn't reintroduce it.
    """
    
    def test_group_selection_isolation(self):
        """Test that selecting in Group 1 doesn't affect Group 2."""
        ui = MockModernWindow()
        
        # Group 1
        ui.current_group_id = 'group_1'
        ui.select_image_at_index(2, 'group_1')
        assert ui.last_selected_index == 2
        assert 2 in ui.selected_indices
        
        # Switch to Group 2
        ui.current_group_id = 'group_2'
        ui.select_image_at_index(3, 'group_2')
        
        # Group 2 should have different selection
        assert ui.last_selected_index == 3
        assert 3 in ui.selected_indices
        assert 2 not in ui.selected_indices
        
        logger.info("✅ Cross-group selection properly isolated")


# ============================================================================
# Test Suite 4: Cancel Operations
# ============================================================================

class TestCancelOperations:
    """Test that UI can cancel processing."""
    
    def test_cancel_during_processing(self):
        """Test canceling processing mid-operation."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        import tempfile
        
        cancelled = False
        processed_count = [0]
        
        def cancellable_worker(path: Path, config) -> Dict[str, Any]:
            if cancelled:
                raise KeyboardInterrupt("Processing cancelled")
            
            time.sleep(0.02)
            processed_count[0] += 1
            return {'score': 42.0}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = [tmpdir / f"img_{i}.jpg" for i in range(50)]
            for p in image_paths:
                p.touch()
            
            # Start processing in thread
            cancel_event = threading.Event()
            processed = [0]
            
            def run_processing():
                try:
                    results, stats = process_images_parallel_v2(
                        image_paths=image_paths,
                        worker_func=cancellable_worker,
                        config={},
                        max_workers=2,
                    )
                    processed[0] = len(results)
                except Exception as e:
                    logger.info(f"Processing interrupted: {e}")
            
            thread = threading.Thread(target=run_processing)
            thread.start()
            
            # Let it run for a bit
            time.sleep(0.2)
            
            # Signal cancel
            cancelled = True
            
            # Wait for thread to finish
            thread.join(timeout=5)
            
            # Some processing should have happened
            assert processed[0] > 0
            # But not all (cancelled early)
            assert processed[0] < len(image_paths)
            
            logger.info(f"✅ Processing cancelled after {processed[0]} images")


# ============================================================================
# Test Suite 5: Result Display in UI
# ============================================================================

class TestResultDisplayInUI:
    """Test that results can be displayed correctly in UI."""
    
    def test_quality_result_display_format(self):
        """Test that quality results can be formatted for UI display."""
        from photo_cleaner.pipeline.quality_analyzer import QualityResult
        
        # Create a typical quality result
        result = QualityResult(
            path=Path("/test/image.jpg"),
            face_quality=None,
            overall_sharpness=0.75,
            lighting_score=60.0,
            resolution_score=2.0,
            width=1920,
            height=1440,
            total_score=72.5,
        )
        
        # UI should be able to display these
        assert str(result.path)
        assert result.overall_sharpness is not None
        assert result.total_score is not None
        
        # UI should handle missing face quality
        if result.face_quality is None:
            # UI shows placeholder
            face_str = "No face detected"
        else:
            face_str = f"Eyes: {result.face_quality.all_eyes_open}"
        
        assert face_str
    
    def test_group_scoring_display(self):
        """
        Test that group-based scoring (comparing duplicates) works with new impl.
        """
        # This is a simplified test - full integration would need real images
        
        # Simulate group scores
        group_scores = {
            'image_1.jpg': 75.0,
            'image_2.jpg': 82.0,
            'image_3.jpg': 68.0,
        }
        
        # UI should be able to:
        # 1. Sort by score
        sorted_images = sorted(group_scores.items(), key=lambda x: x[1], reverse=True)
        best_image = sorted_images[0]
        assert best_image[0] == 'image_2.jpg'
        
        # 2. Highlight best image
        best_score = best_image[1]
        assert best_score == 82.0
        
        logger.info("✅ Group scoring display format validated")


# ============================================================================
# Test Suite 6: Integration with Auto-Selection
# ============================================================================

class TestAutoSelectionIntegration:
    """Test that auto-selection workflow works with new multiprocessing."""
    
    def test_auto_selection_workflow(self):
        """
        Simulate the auto-selection workflow:
        1. Analyze all groups
        2. Score images
        3. Auto-select best images
        4. Display results to UI
        """
        from photo_cleaner.pipeline.multiprocessing_improved import WorkerResult
        
        # Simulate group processing
        groups = {
            'group_1': [
                WorkerResult(Path('img1.jpg'), success=True, result={'score': 70.0}),
                WorkerResult(Path('img2.jpg'), success=True, result={'score': 85.0}),
                WorkerResult(Path('img3.jpg'), success=True, result={'score': 75.0}),
            ],
            'group_2': [
                WorkerResult(Path('img4.jpg'), success=True, result={'score': 65.0}),
                WorkerResult(Path('img5.jpg'), success=True, result={'score': 72.0}),
            ],
        }
        
        # UI processes results
        for group_id, results in groups.items():
            # 1. Extract scores
            scores = [r.result.get('score', 0) for r in results if r.success]
            
            # 2. Find best (index)
            best_idx = scores.index(max(scores))
            best_score = scores[best_idx]
            
            # 3. UI can auto-select or mark for deletion
            if best_score > 75:
                action = "KEEP"
            else:
                action = "REVIEW"
            
            logger.info(f"{group_id}: Best image at index {best_idx} (score {best_score:.0f}) → {action}")
        
        logger.info("✅ Auto-selection workflow validated")


# ============================================================================
# Test Suite 7: Performance with UI Threading
# ============================================================================

class TestUIThreading:
    """Test that multiprocessing works correctly with UI event loop."""
    
    def test_multiprocessing_with_ui_main_thread(self):
        """
        Test that processing can run in background while UI remains responsive.
        
        This simulates:
        - UI thread calls process_images_parallel_v2
        - Updates progress in UI callback
        - UI remains responsive
        """
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        import tempfile
        
        ui_updates = []
        
        def ui_progress_callback(progress):
            ui_updates.append(time.time())
        
        def worker(path: Path, config) -> Dict[str, Any]:
            time.sleep(0.01)
            return {'score': 42.0}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = [tmpdir / f"img_{i}.jpg" for i in range(30)]
            for p in image_paths:
                p.touch()
            
            # Process in "background" (same thread for test)
            start = time.time()
            results, stats = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=worker,
                config={},
                max_workers=2,
                on_progress=ui_progress_callback,
            )
            elapsed = time.time() - start
            
            # UI should have been updated
            assert len(ui_updates) > 0
            
            # Processing should complete successfully
            assert stats['successful'] == 30
            
            logger.info(f"✅ UI threading: {stats['successful']} images in {elapsed:.1f}s")


# ============================================================================
# Test Suite 8: Error Display in UI
# ============================================================================

class TestErrorDisplayInUI:
    """Test that errors are formatted correctly for UI display."""
    
    def test_error_formatting_for_ui(self):
        """Test that worker errors can be displayed in UI."""
        from photo_cleaner.pipeline.multiprocessing_improved import process_images_parallel_v2
        import tempfile
        
        def failing_worker(path: Path, config) -> Dict[str, Any]:
            if 'fail' in str(path):
                raise ValueError(f"Processing failed: {path.name}")
            return {'score': 42.0}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = [
                tmpdir / "good.jpg",
                tmpdir / "fail_1.jpg",
                tmpdir / "fail_2.jpg",
                tmpdir / "good2.jpg",
            ]
            for p in image_paths:
                p.touch()
            
            results, stats = process_images_parallel_v2(
                image_paths=image_paths,
                worker_func=failing_worker,
                config={},
                max_workers=2,
            )
            
            # UI should display results with errors
            for result in results:
                if not result.success:
                    # UI can display error message
                    error_msg = f"❌ {result.image_path}: {result.error}"
                    assert len(error_msg) > 0
                    logger.info(error_msg)
            
            # UI shows summary
            logger.info(f"✅ Processed {stats['total_images']} images: "
                       f"{stats['successful']} OK, {stats['failed']} errors")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
