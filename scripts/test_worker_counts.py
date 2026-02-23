#!/usr/bin/env python3
"""
Test verschiedene worker counts für Indexing.

Phase 2 Week 4: Find optimal parallelism level.
"""

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from photo_cleaner.core.indexer import PhotoIndexer
from photo_cleaner.db.schema import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_worker_count(test_data_path: str, worker_count: int):
    """Test indexing with specific worker count."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing with {worker_count} workers")
    logger.info("=" * 60)
    
    # Setup test database
    db_path = Path(f"test_data_system/test_workers_{worker_count}.db")
    if db_path.exists():
        db_path.unlink()
    
    db = Database(str(db_path))
    db.connect()
    
    # Create indexer WITHOUT async writes (back to baseline)
    indexer = PhotoIndexer(db, max_workers=worker_count)
    
    # Start timing
    start_time = time.time()
    
    # Run indexing
    stats = indexer.index_folder(Path(test_data_path), skip_existing=False)
    
    duration = time.time() - start_time
    
    # Cleanup
    db.close()
    db_path.unlink()
    
    return {
        "worker_count": worker_count,
        "duration": duration,
        "images": stats["processed"],
        "per_image_ms": (duration / stats["processed"]) * 1000
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-data", required=True)
    parser.add_argument("--output", default="results/worker_count_test.json")
    
    args = parser.parse_args()
    
    # Test different worker counts
    results = []
    for workers in [1, 2, 4, 8]:
        result = test_worker_count(args.test_data, workers)
        results.append(result)
        logger.info(f"\n{workers} workers: {result['duration']:.2f}s ({result['per_image_ms']:.1f}ms/image)")
    
    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n\nResults saved to: {args.output}")
    logger.info("\nSummary:")
    for r in results:
        logger.info(f"  {r['worker_count']} workers: {r['duration']:.2f}s ({r['per_image_ms']:.1f}ms/img)")
