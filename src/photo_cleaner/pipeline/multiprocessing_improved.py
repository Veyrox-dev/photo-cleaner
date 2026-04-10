"""
Improved Multiprocessing Pipeline - Lock-Free Implementation

This module replaces multiprocessing_manager.py with a robust,
lock-free implementation using Queue-based job distribution.

Key improvements:
1. NO shared state or locks -> Zero contention
2. FIFO result ordering -> Correct group-based scoring
3. Graceful shutdown with SENTINEL pattern
4. Per-worker exception handling
5. Optional progress tracking (separate mechanism)

Architecture:
  Main process:
    - Creates job_queue, result_queue
    - Populates jobs
    - Starts N workers
    - Collects results in order

  Worker process:
    - Loop: get job, process, put result
    - Exit on SENTINEL marker
"""

import logging
import time
import traceback
import pickle
from dataclasses import dataclass, field
from multiprocessing import Queue, Process, cpu_count
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable

logger = logging.getLogger(__name__)

# Sentinel value to signal worker shutdown
_SENTINEL = None


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
class ProgressSnapshot:
    """Snapshot of current progress (no locks)."""
    
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
    def success_rate(self) -> float:
        """Get success rate."""
        if self.processed == 0:
            return 0.0
        return ((self.processed - self.failed) / self.processed) * 100.0

    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimate time remaining (very rough)."""
        if self.processed == 0:
            return None
        elapsed = time.time() - self.timestamp
        per_image = elapsed / self.processed
        remaining = self.total - self.processed
        return per_image * remaining


def _worker_process_loop(
    job_queue: Queue,
    result_queue: Queue,
    worker_id: int,
) -> None:
    """
    Worker process main loop.
    
    Processes jobs from queue until SENTINEL is received.
    Each job contains: (worker_func, image_path, config)
    
    Args:
        job_queue: Queue for receiving jobs
        result_queue: Queue for returning results
        worker_id: Worker process ID (for logging)
    """
    logger.info(f"Worker {worker_id} started")
    processed = 0
    
    while True:
        try:
            # Get next job (blocking, with timeout for safety)
            job = job_queue.get(timeout=300)  # 5 minute timeout
            
            # Check for sentinel (shutdown signal)
            if job is _SENTINEL:
                logger.info(f"Worker {worker_id} received SENTINEL, shutting down (processed {processed})")
                break
            
            # Unpack job
            worker_func, image_path, config = job
            start_time = time.time()
            
            try:
                # Process image
                result_data = worker_func(image_path, config)
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Create result object
                result = WorkerResult(
                    image_path=image_path,
                    success=True,
                    result=result_data,
                    processing_time_ms=elapsed_ms,
                )
                processed += 1
                
            except Exception as e:
                # Per-image exception handling
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(f"Worker {worker_id}: Error processing {image_path}: {e}")
                
                result = WorkerResult(
                    image_path=image_path,
                    success=False,
                    error=str(e),
                    error_traceback=traceback.format_exc(),
                    processing_time_ms=elapsed_ms,
                )
            
            # Put result in queue (blocking put is ok, backpressure is good)
            result_queue.put(result)
        
        except Exception as e:
            logger.error(f"Worker {worker_id} fatal error: {e}")
            break
    
    logger.info(f"Worker {worker_id} exit")


class QueueBasedWorkerPool:
    """
    Lock-free worker pool using Queue-based job distribution.
    
    This replaces the old WorkerPool with a simpler, more robust
    implementation that avoids all the Lock contention issues.
    """
    
    def __init__(
        self,
        worker_func: Callable,
        num_images: int,
        max_workers: Optional[int] = None,
        timeout_per_task: int = 300,
    ):
        """
        Initialize pool.
        
        Args:
            worker_func: Function to process one image (path, config) -> dict
            num_images: Total images to process (for progress tracking)
            max_workers: Number of workers (None = auto-detect cores-1)
            timeout_per_task: Timeout in seconds (not enforced in workers)
        """
        # Determine worker count
        cpu_cores = cpu_count() or 4
        if max_workers is None:
            max_workers = max(1, cpu_cores - 1)
        else:
            max_workers = min(max_workers, cpu_cores - 1)
        
        self.worker_func = worker_func
        self.num_images = num_images
        self.max_workers = max_workers
        self.timeout_per_task = timeout_per_task
        
        # Create queues (unbuffered is ok, backpressure is healthy)
        self.job_queue: Optional[Queue] = None
        self.result_queue: Optional[Queue] = None
        self.worker_processes: List[Process] = []
        
        self._start_time = time.time()
        
        logger.info(
            f"QueueBasedWorkerPool initialized: {self.max_workers} workers, "
            f"{self.num_images} images"
        )
    
    def __enter__(self):
        """Context manager entry: start workers."""
        self.job_queue = Queue()
        self.result_queue = Queue()
        
        # Start worker processes
        for worker_id in range(self.max_workers):
            p = Process(
                target=_worker_process_loop,
                args=(self.job_queue, self.result_queue, worker_id),
                daemon=False,
            )
            p.start()
            self.worker_processes.append(p)
        
        logger.info(f"Started {self.max_workers} worker processes")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: shutdown workers.
        
        BUG #2 FIX: Force-kill workers that don't respond to terminate().
        """
        if self.job_queue is None:
            return
        
        logger.info("Shutting down worker pool...")
        
        # Send SENTINEL to each worker to signal shutdown
        for _ in range(self.max_workers):
            try:
                self.job_queue.put(_SENTINEL, timeout=1)
            except Exception as e:
                logger.warning(f"Failed to send SENTINEL: {e}")
        
        # Wait for all workers to exit with progressive force
        zombies = []
        for i, p in enumerate(self.worker_processes):
            # Phase 1: Graceful shutdown (10s)
            p.join(timeout=10)
            if not p.is_alive():
                continue
            
            # Phase 2: SIGTERM (2s)
            logger.warning(f"Worker {i} did not exit gracefully, terminating...")
            p.terminate()
            p.join(timeout=2)
            if not p.is_alive():
                continue
            
            # BUG #2 FIX: Phase 3: SIGKILL (force)
            logger.error(f"Worker {i} did not respond to terminate(), force-killing...")
            try:
                p.kill()  # Force-kill the process
                p.join(timeout=1)
                if p.is_alive():
                    zombies.append(i)
                    logger.critical(f"Worker {i} is now a zombie (unkillable)")
            except Exception as e:
                logger.error(f"Failed to kill worker {i}: {e}")
                zombies.append(i)
        
        # BUG #2 FIX: Cleanup queues to prevent resource leak
        try:
            # Drain job queue
            while not self.job_queue.empty():
                try:
                    self.job_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Drain result queue
            while not self.result_queue.empty():
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Close queue handles
            self.job_queue.close()
            self.result_queue.close()
            self.job_queue.join_thread()
            self.result_queue.join_thread()
        except Exception as e:
            logger.warning(f"Queue cleanup error: {e}")
        
        self.worker_processes.clear()
        
        if zombies:
            logger.critical(f"Worker pool shutdown incomplete: {len(zombies)} zombie processes remain (PIDs: {zombies})")
        else:
            logger.info("Worker pool shut down complete")
    
    def process_images(
        self,
        image_paths: List[Path],
        config: Any,
        on_progress: Optional[Callable[[ProgressSnapshot], None]] = None,
    ) -> Tuple[List[WorkerResult], ProgressSnapshot]:
        """
        Process all images using the worker pool.
        
        IMPORTANT: Results are returned in the SAME ORDER as image_paths!
        This is critical for group-based scoring.
        
        Args:
            image_paths: List of image paths (in order)
            config: Configuration object (immutable, passed to workers)
            on_progress: Optional callback(progress: ProgressSnapshot)
        
        Returns:
            (results_in_order, final_progress)
        """
        if self.job_queue is None or self.result_queue is None:
            raise RuntimeError("Pool not initialized. Use 'with QueueBasedWorkerPool(...)'")
        
        # Map: image_path -> result (for reordering at end)
        results_by_path: Dict[str, WorkerResult] = {}
        
        # Populate job queue
        for image_path in image_paths:
            job = (self.worker_func, image_path, config)
            self.job_queue.put(job)
        
        logger.info(f"Submitted {len(image_paths)} jobs to queue")
        
        # Collect results
        processed = 0
        failed = 0
        last_progress_time = time.time()
        
        for i in range(len(image_paths)):
            try:
                # Get result (blocking)
                result = self.result_queue.get(timeout=self.timeout_per_task * 2)
                
                # Store by path for reordering
                path_str = str(result.image_path)
                results_by_path[path_str] = result
                
                processed += 1
                if not result.success:
                    failed += 1
                
                # Optional progress callback (rate-limited)
                now = time.time()
                if on_progress and (now - last_progress_time) >= 1.0:
                    progress = ProgressSnapshot(
                        processed=processed,
                        total=len(image_paths),
                        failed=failed,
                        timestamp=self._start_time,
                    )
                    on_progress(progress)
                    last_progress_time = now
            
            except Exception as e:
                logger.error(f"Error collecting result {i+1}/{len(image_paths)}: {e}")
                # Continue collecting other results

        # Ensure progress callback receives a final update
        if on_progress:
            on_progress(
                ProgressSnapshot(
                    processed=processed,
                    total=len(image_paths),
                    failed=failed,
                    timestamp=self._start_time,
                )
            )
        
        # Reorder results to match input order (CRITICAL for scoring!)
        results = []
        for image_path in image_paths:
            path_str = str(image_path)
            if path_str in results_by_path:
                results.append(results_by_path[path_str])
            else:
                logger.error(f"Missing result for {image_path}")
                results.append(WorkerResult(
                    image_path=image_path,
                    success=False,
                    error="Result not received",
                ))
        
        # Final progress snapshot
        final_progress = ProgressSnapshot(
            processed=processed,
            total=len(image_paths),
            failed=failed,
            timestamp=self._start_time,
        )
        
        logger.info(
            f"Processing complete: {processed}/{len(image_paths)} results collected "
            f"({final_progress.success_rate:.1f}% success rate)"
        )
        
        return results, final_progress


def process_images_parallel_v2(
    image_paths: List[Path],
    worker_func: Callable,
    config: Any,
    max_workers: Optional[int] = None,
    timeout_per_task: int = 300,
    on_progress: Optional[Callable[[ProgressSnapshot], None]] = None,
) -> Tuple[List[WorkerResult], Dict[str, Any]]:
    """
    High-level API for parallel image processing (improved version).
    
    Drop-in replacement for process_images_parallel() from old module.
    
    Key differences:
    1. Lock-free implementation (Queue-based)
    2. GUARANTEED result ordering (group scoring works)
    3. No Manager() overhead
    4. Simpler, more robust exception handling
    
    Args:
        image_paths: List of image paths to process
        worker_func: Function to process one image (path, config) -> dict
        config: Configuration object (read-only, immutable)
        max_workers: Number of workers (None = auto-detect)
        timeout_per_task: Timeout in seconds for result retrieval/worker tasks
        on_progress: Optional callback(progress: ProgressSnapshot)
    
    Returns:
        (results, statistics)
    """
    if not image_paths:
        return [], {
            "total_images": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 100.0,
            "total_time_ms": 0.0,
            "mean_time_per_image_ms": 0.0,
        }
    
    start_time = time.time()

    # Fallback: If worker/config is not picklable, run sequentially in-process.
    try:
        pickle.dumps((worker_func, config))
    except Exception:
        logger.warning("Worker or config not picklable; falling back to sequential processing")
        results: List[WorkerResult] = []
        processed = 0
        failed = 0
        cancelled = False

        for image_path in image_paths:
            task_start = time.time()
            try:
                result_data = worker_func(image_path, config)
                elapsed_ms = (time.time() - task_start) * 1000
                result = WorkerResult(
                    image_path=image_path,
                    success=True,
                    result=result_data,
                    processing_time_ms=elapsed_ms,
                )
            except KeyboardInterrupt:
                logger.info("Processing cancelled in sequential fallback")
                cancelled = True
                break
            except Exception as e:
                elapsed_ms = (time.time() - task_start) * 1000
                result = WorkerResult(
                    image_path=image_path,
                    success=False,
                    error=str(e),
                    error_traceback=traceback.format_exc(),
                    processing_time_ms=elapsed_ms,
                )
                failed += 1

            results.append(result)
            processed += 1

            if on_progress:
                on_progress(
                    ProgressSnapshot(
                        processed=processed,
                        total=len(image_paths),
                        failed=failed,
                        timestamp=start_time,
                    )
                )

        if cancelled and on_progress:
            on_progress(
                ProgressSnapshot(
                    processed=processed,
                    total=len(image_paths),
                    failed=failed,
                    timestamp=start_time,
                )
            )

        total_time_ms = (time.time() - start_time) * 1000
        successful = len(results) - failed
        stats = {
            "total_images": len(image_paths),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(image_paths) * 100) if results else 0.0,
            "total_time_ms": total_time_ms,
            "mean_time_per_image_ms": total_time_ms / len(results) if results else 0.0,
        }

        return results, stats
    
    with QueueBasedWorkerPool(
        worker_func=worker_func,
        num_images=len(image_paths),
        max_workers=max_workers,
        timeout_per_task=timeout_per_task,
    ) as pool:
        results, final_progress = pool.process_images(
            image_paths, config, on_progress=on_progress
        )
    
    # Calculate statistics
    total_time_ms = (time.time() - start_time) * 1000
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    
    stats = {
        "total_images": len(image_paths),
        "successful": successful,
        "failed": failed,
        "success_rate": (successful / len(image_paths) * 100) if results else 0.0,
        "total_time_ms": total_time_ms,
        "mean_time_per_image_ms": total_time_ms / len(results) if results else 0.0,
    }
    
    logger.info(
        f"Parallel processing complete: {stats['successful']}/{stats['total_images']} "
        f"successful ({stats['success_rate']:.1f}%), "
        f"total time {stats['total_time_ms']:.0f}ms"
    )
    
    return results, stats


# For backward compatibility, export the new classes
__all__ = [
    'WorkerResult',
    'ProgressSnapshot',
    'QueueBasedWorkerPool',
    'process_images_parallel_v2',
]
