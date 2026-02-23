"""
Multiprocessing Pipeline Manager for PhotoCleaner

Provides robust, scalable image processing with:
- Automatic CPU core detection and worker pool management
- Per-image exception handling and fault tolerance
- Process-safe progress tracking
- Optional batching for efficiency
- Memory-efficient result aggregation
"""

import logging
import os
import time
import pickle
import threading
from dataclasses import dataclass, field
from multiprocessing import Pool, Queue, cpu_count
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict
import traceback

logger = logging.getLogger(__name__)


class _Counter:
    """Lightweight counter with .value attribute (Manager-compatible surface)."""

    def __init__(self, value: int = 0) -> None:
        self.value = value


@dataclass
class WorkerResult:
    """Result from a single worker process."""
    
    image_path: Path
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    processing_time_ms: float = 0.0
    
    def __post_init__(self):
        """Ensure paths are strings for pickling."""
        if isinstance(self.image_path, Path):
            self.image_path = str(self.image_path)


@dataclass
class ProgressUpdate:
    """Progress information from workers."""
    
    processed: int = 0
    total: int = 0
    failed: int = 0
    timestamp: float = field(default_factory=time.time)
    
    @property
    def progress_percent(self) -> float:
        """Get progress as percentage."""
        if self.total == 0:
            return 0.0
        return (self.processed / self.total) * 100.0
    
    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimate time remaining (very rough)."""
        if self.processed == 0:
            return None
        elapsed = time.time() - self.timestamp
        per_image = elapsed / self.processed
        remaining = self.total - self.processed
        return per_image * remaining


class ProgressTracker:
    """Thread-safe progress tracking."""
    
    def __init__(self, total: int):
        """Initialize progress tracker.
        
        Args:
            total: Total number of items to process
        """
        self.total = total
        self._lock = threading.Lock()
        self._processed = _Counter(0)
        self._failed = _Counter(0)
        self._start_time = time.time()
        self._last_update_time = self._start_time
    
    def increment(self, count: int = 1, failed: bool = False):
        """Increment progress counter.
        
        Args:
            count: Number of items processed
            failed: Whether the items failed
        """
        with self._lock:
            self._processed.value += count
            if failed:
                self._failed.value += count
    
    def get_current(self) -> ProgressUpdate:
        """Get current progress state."""
        with self._lock:
            return ProgressUpdate(
                processed=self._processed.value,
                total=self.total,
                failed=self._failed.value,
                timestamp=self._start_time,
            )
    
    def print_progress(self, force: bool = False):
        """Print progress update (rate-limited).
        
        Args:
            force: Force print even if not enough time passed
        """
        now = time.time()
        if not force and (now - self._last_update_time) < 1.0:
            return
        
        progress = self.get_current()
        pct = progress.progress_percent
        eta = progress.eta_seconds
        
        eta_str = f"ETA: {int(eta)}s" if eta else "ETA: --"
        logger.info(
            f"Progress: {progress.processed}/{progress.total} "
            f"({pct:.1f}%) | Failed: {progress.failed} | {eta_str}"
        )
        self._last_update_time = now


class WorkerPool:
    """Manages a pool of worker processes."""
    
    def __init__(
        self,
        worker_func: Callable,
        num_images: int,
        max_workers: Optional[int] = None,
        batch_size: int = 1,
        timeout_per_task: int = 300,
    ):
        """
        Initialize worker pool.
        
        Args:
            worker_func: Function to run in each worker (must be pickleable)
            num_images: Total number of images to process
            max_workers: Maximum workers (None = auto-detect)
            batch_size: Images per task (1 = one image per task)
            timeout_per_task: Timeout per task in seconds
        """
        # Determine worker count
        cpu_cores = cpu_count() or 4
        if max_workers is None:
            # Use all but one core
            max_workers = max(1, cpu_cores - 1)
        else:
            max_workers = min(max_workers, cpu_cores - 1)
        
        self.worker_func = worker_func
        self.num_images = num_images
        self.max_workers = max_workers
        self.batch_size = max(1, batch_size)
        self.timeout_per_task = timeout_per_task
        
        self.pool = None
        self.progress_tracker = ProgressTracker(num_images)
        
        logger.info(
            f"WorkerPool initialized: {self.max_workers} workers, "
            f"{self.num_images} images, batch_size={self.batch_size}"
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.pool = Pool(processes=self.max_workers)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.pool is not None:
            self.pool.close()
            self.pool.join()
            self.pool = None
    
    def process_images(
        self,
        image_paths: List[Path],
        config: Any,
    ) -> Tuple[List[WorkerResult], ProgressUpdate]:
        """
        Process all images using worker pool.
        
        Args:
            image_paths: List of paths to process
            config: Configuration object (read-only, passed to workers)
        
        Returns:
            (results, final_progress)
        """
        if self.pool is None:
            raise RuntimeError("Pool not initialized. Use 'with WorkerPool(...)' context.")
        
        results = []
        tasks = []
        
        # Create batches
        batches = self._create_batches(image_paths)
        logger.info(f"Created {len(batches)} tasks from {len(image_paths)} images")
        
        # Submit all tasks
        try:
            pickle.dumps(self.progress_tracker)
            worker_progress = self.progress_tracker
        except Exception:
            logger.warning("Progress tracker not picklable; tracking progress in parent")
            worker_progress = None

        for batch in batches:
            task = self.pool.apply_async(
                _process_batch_wrapper,
                args=(self.worker_func, batch, config, worker_progress),
            )
            tasks.append(task)
        
        # Collect results with progress tracking
        for i, task in enumerate(tasks, 1):
            try:
                batch_results = task.get(timeout=self.timeout_per_task)
                results.extend(batch_results)

                if worker_progress is None:
                    for result in batch_results:
                        self.progress_tracker.increment(count=1, failed=not result.success)
                
                # Print progress every 10 tasks or at end
                if i % 10 == 0 or i == len(tasks):
                    self.progress_tracker.print_progress(force=(i == len(tasks)))
            
            except Exception as e:
                logger.error(f"Task {i} failed: {e}")
                # Extract batch from task for error tracking
                batch = batches[i - 1] if i - 1 < len(batches) else []
                for image_path in batch:
                    results.append(WorkerResult(
                        image_path=image_path,
                        success=False,
                        error=f"Task timeout or error: {str(e)}",
                        error_traceback=traceback.format_exc(),
                    ))
        
        final_progress = self.progress_tracker.get_current()
        return results, final_progress
    
    def _create_batches(self, image_paths: List[Path]) -> List[List[Path]]:
        """Create batches of images for processing.
        
        Args:
            image_paths: All image paths
        
        Returns:
            List of batches (each batch is a list of paths)
        """
        batches = []
        for i in range(0, len(image_paths), self.batch_size):
            batch = image_paths[i:i + self.batch_size]
            batches.append(batch)
        return batches


def _process_batch_wrapper(
    worker_func: Callable,
    batch: List[Path],
    config: Any,
    progress_tracker: Optional['ProgressTracker'] = None,
) -> List[WorkerResult]:
    """
    Wrapper function for processing a batch of images in a worker.
    
    This runs in a worker process. It handles exceptions per-image
    and updates progress safely.
    
    Args:
        worker_func: Function to process a single image
        batch: List of image paths
        config: Configuration object
        progress_tracker: Optional progress tracker
    
    Returns:
        List of WorkerResult objects
    """
    results = []
    
    for image_path in batch:
        start_time = time.time()
        
        try:
            # Call worker function
            result = worker_func(image_path, config)
            
            # Worker should return a dict
            elapsed_ms = (time.time() - start_time) * 1000
            results.append(WorkerResult(
                image_path=image_path,
                success=True,
                result=result,
                processing_time_ms=elapsed_ms,
            ))
        
        except Exception as e:
            # Catch all exceptions per-image
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Error processing {image_path}: {e}")
            results.append(WorkerResult(
                image_path=image_path,
                success=False,
                error=str(e),
                error_traceback=traceback.format_exc(),
                processing_time_ms=elapsed_ms,
            ))
        
        # Update progress
        if progress_tracker:
            progress_tracker.increment(count=1, failed=not results[-1].success)
    
    return results


class ResultAggregator:
    """Aggregates and deduplicates results from workers."""
    
    def __init__(self):
        """Initialize aggregator."""
        self.results_by_path: Dict[str, WorkerResult] = {}
        self.failed_images: List[Path] = []
        self.successful_images: List[Path] = []
    
    def add_results(self, results: List[WorkerResult]):
        """Add worker results.
        
        Args:
            results: List of WorkerResult objects
        """
        for result in results:
            path_str = str(result.image_path)
            self.results_by_path[path_str] = result
            
            if result.success:
                self.successful_images.append(Path(result.image_path))
            else:
                self.failed_images.append(Path(result.image_path))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregation statistics.
        
        Returns:
            Dict with processing statistics
        """
        total = len(self.results_by_path)
        successful = len(self.successful_images)
        failed = len(self.failed_images)
        
        total_time_ms = sum(
            r.processing_time_ms for r in self.results_by_path.values()
        )
        
        return {
            "total_images": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "total_time_ms": total_time_ms,
            "mean_time_per_image_ms": total_time_ms / total if total > 0 else 0.0,
        }


# ============================================================================
# Public API for Easy Integration
# ============================================================================

def process_images_parallel(
    image_paths: List[Path],
    worker_func: Callable,
    config: Any,
    max_workers: Optional[int] = None,
    batch_size: int = 1,
    on_progress: Optional[Callable] = None,
) -> Tuple[List[WorkerResult], Dict[str, Any]]:
    """
    Process images in parallel using multiprocessing.
    
    Simple, high-level interface for image processing.
    
    Args:
        image_paths: List of image paths to process
        worker_func: Function to process one image (path, config) -> dict
        config: Configuration object (read-only)
        max_workers: Number of workers (None = auto-detect)
        batch_size: Images per task
        on_progress: Optional callback(progress: ProgressUpdate)
    
    Returns:
        (results, statistics)
    """
    if not image_paths:
        return [], {
            "total_images": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 100.0,
        }
    
    with WorkerPool(
        worker_func=worker_func,
        num_images=len(image_paths),
        max_workers=max_workers,
        batch_size=batch_size,
    ) as pool:
        results, final_progress = pool.process_images(image_paths, config)
    
    # Aggregate results
    aggregator = ResultAggregator()
    aggregator.add_results(results)
    stats = aggregator.get_statistics()
    
    if on_progress:
        on_progress(final_progress)
    
    logger.info(
        f"Parallel processing complete: {stats['successful']}/{stats['total_images']} "
        f"successful ({stats['success_rate']:.1f}%), "
        f"total time {stats['total_time_ms']:.0f}ms"
    )
    
    return results, stats
