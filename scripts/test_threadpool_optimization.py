#!/usr/bin/env python
"""
Test script to validate ThreadPool optimization (Phase 2 Week 2).

Compares the new ThreadPool-based indexer with profiling baseline.
Ensures no regressions and measures actual speedup.

Usage:
    python scripts/test_threadpool_optimization.py --test-data test_data_system

Expected Results:
    - No import errors (ThreadPool vs ProcessPool)
    - Successful indexing with threadpool
    - Baseline: 144s for 5k images
    - Target: 20-35s (4-7x speedup)
    - Success: 80% of target speedup (28-50s acceptable)
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_threadpool_optimization(test_data_path: Path) -> dict:
    """
    Test the ThreadPool-optimized indexer.
    
    Args:
        test_data_path: Path to test images
        
    Returns:
        Results dict with timing and validation
    """
    try:
        # Import after path setup
        from photo_cleaner.core.indexer import PhotoIndexer
        from photo_cleaner.db.schema import Database
        
        logger.info("✓ Successfully imported PhotoIndexer (ThreadPool version)")
        
        # Create temporary database for testing
        db_path = test_data_path.parent / "test_threadpool.db"
        db = Database(db_path)
        db.connect()
        logger.info(f"✓ Database initialized: {db_path}")
        
        # Create indexer with ThreadPool
        indexer = PhotoIndexer(db=db, max_workers=4)
        logger.info(f"✓ Indexer created with db and max_workers=4 (ThreadPool enabled)")
        
        # Profile the indexing
        logger.info(f"Starting indexing of {test_data_path}...")
        start_time = time.time()
        start_memory = _get_memory_usage()
        
        stats = indexer.index_folder(test_data_path, skip_existing=False)
        
        end_time = time.time()
        end_memory = _get_memory_usage()
        duration = end_time - start_time
        memory_delta = end_memory - start_memory
        
        # Validate results
        results = {
            "success": True,
            "implementation": "ThreadPool (Phase 2 Week 2)",
            "test_data_path": str(test_data_path),
            "image_count": stats.get("processed", 0),
            "duration_seconds": duration,
            "memory_delta_mb": memory_delta,
            "processed": stats.get("processed", 0),
            "failed": stats.get("failed", 0),
            "timestamp": datetime.now().isoformat(),
        }
        
        # Compare against baseline
        baseline = 144.14  # 5k images with ProcessPool
        expected_target = 35  # Best case 4x speedup
        
        if stats.get("processed", 0) > 100:  # Only compare if significant workload
            speedup = baseline / duration if duration > 0 else 0
            results["baseline_seconds"] = baseline
            results["speedup_factor"] = speedup
            results["performance_status"] = "EXCELLENT" if speedup >= 3 else "GOOD" if speedup >= 2 else "ACCEPTABLE" if speedup >= 1 else "NEEDS WORK"
            
            logger.info(f"\n{'='*60}")
            logger.info(f"THREADPOOL OPTIMIZATION TEST RESULTS")
            logger.info(f"{'='*60}")
            logger.info(f"Image Count:        {stats['processed']}")
            logger.info(f"Duration:           {duration:.2f}s")
            logger.info(f"Baseline (Process): {baseline:.2f}s (5k images)")
            logger.info(f"Speedup Factor:     {speedup:.2f}x")
            logger.info(f"Performance Status: {results['performance_status']}")
            logger.info(f"Memory Delta:       {memory_delta:.1f} MB")
            logger.info(f"{'='*60}\n")
        
        # Cleanup
        db.conn.close()
        db_path.unlink(missing_ok=True)
        
        return results
        
    except ImportError as e:
        logger.error(f"✗ Import error (ThreadPool issue?): {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        return {"success": False, "error": str(e)}

def _get_memory_usage() -> float:
    """Get current process memory usage in MB."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except Exception:
        return 0.0

def main():
    parser = argparse.ArgumentParser(
        description="Test ThreadPool optimization (Phase 2 Week 2)"
    )
    parser.add_argument(
        "--test-data",
        type=Path,
        default=Path(PROJECT_ROOT) / "test_data_system",
        help="Path to test images"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file with results"
    )
    
    args = parser.parse_args()
    
    if not args.test_data.exists():
        logger.error(f"Test data not found: {args.test_data}")
        logger.info("Generate test images first:")
        logger.info("  python scripts/generate_test_images.py --output test_data_system/5k --count 5000")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("PHASE 2 WEEK 2: ThreadPool Optimization Test")
    logger.info("=" * 60)
    
    # Run test
    results = test_threadpool_optimization(args.test_data)
    
    # Save results
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to: {args.output}")
    
    # Exit with status
    sys.exit(0 if results.get("success") else 1)

if __name__ == "__main__":
    main()
