#!/usr/bin/env python3
"""
Stress testing script for PhotoCleaner v0.8.3

Generates large test image datasets and runs photocleaner on them,
measuring performance, memory usage, and timing characteristics.

Usage:
    python scripts/stress_test_images.py
    
Modes:
    - generate-10k: Create 10,000 images directory
    - generate-50k: Create 50,000 images directory
    - generate-100k: Create 100,000 images directory
    - test-10k: Run photocleaner on 10k dataset
    - test-50k: Run photocleaner on 50k dataset
    - test-100k: Run photocleaner on 100k dataset
    - full: Generate and test all three sizes
"""

import os
import shutil
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
TEST_DATA_DIR = PROJECT_ROOT / "test_data_e2e" / "images"
STRESS_TEST_DIR = PROJECT_ROOT / "stress_test_datasets"
RESULTS_FILE = PROJECT_ROOT / "stress_test_results.json"


def get_image_count(directory: Path) -> int:
    """Count JPEG and HEIC files in directory tree."""
    return len(list(directory.rglob("*.jpg"))) + len(list(directory.rglob("*.heic")))


def generate_dataset(target_images: int, dataset_name: str) -> Path:
    """
    Generate a test dataset by replicating images from test_data_e2e.
    
    Args:
        target_images: Number of images to generate
        dataset_name: Name of the dataset (e.g., '10k', '50k')
        
    Returns:
        Path to generated dataset
    """
    dataset_dir = STRESS_TEST_DIR / dataset_name
    
    if not TEST_DATA_DIR.exists():
        raise FileNotFoundError(f"Source test data not found: {TEST_DATA_DIR}")
    
    source_images = list(TEST_DATA_DIR.glob("*.jpg")) + list(TEST_DATA_DIR.glob("*.heic"))
    if not source_images:
        raise FileNotFoundError(f"No images found in {TEST_DATA_DIR}")
    
    logger.info(f"Generating {target_images} images from {len(source_images)} source images")
    
    # Clean up if exists
    if dataset_dir.exists():
        logger.info(f"Removing existing dataset: {dataset_dir}")
        shutil.rmtree(dataset_dir)
    
    dataset_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate images by cycling through source images
    copied = 0
    for i in range(target_images):
        source = source_images[i % len(source_images)]
        dest_name = f"stress_test_{i:06d}{source.suffix}"
        dest_path = dataset_dir / dest_name
        
        shutil.copy2(source, dest_path)
        copied += 1
        
        if (i + 1) % 1000 == 0:
            logger.info(f"  Generated {i + 1}/{target_images} images...")
    
    actual_count = get_image_count(dataset_dir)
    logger.info(f"✅ Dataset generated: {dataset_dir} ({actual_count} images)")
    
    return dataset_dir


def get_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def run_photocleaner_stress_test(dataset_dir: Path, test_name: str) -> dict:
    """
    Run photocleaner on a stress test dataset, measuring performance.
    
    Args:
        dataset_dir: Path to image dataset
        test_name: Name of the test (e.g., '10k', '50k')
        
    Returns:
        Dictionary with timing and memory metrics
    """
    image_count = get_image_count(dataset_dir)
    dataset_size_bytes = get_directory_size(dataset_dir)
    dataset_size_mb = dataset_size_bytes / (1024 * 1024)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"STRESS TEST: {test_name}")
    logger.info(f"{'='*70}")
    logger.info(f"Dataset: {dataset_dir}")
    logger.info(f"Image count: {image_count:,}")
    logger.info(f"Dataset size: {dataset_size_mb:.1f} MB")
    
    start_time = time.time()
    start_memory_percent = get_memory_percent()
    
    try:
        # Run direct Python script that uses PhotoCleaner modules
        dataset_path = str(dataset_dir).replace('\\', '/')
        project_path = str(PROJECT_ROOT).replace('\\', '/')
        
        test_script = f"""
import sys
import os
sys.path.insert(0, r'{project_path}/src')
os.environ['PHOTOCLEANER_FACE_DETECTOR'] = 'haar'
os.environ['PHOTOCLEANER_EYE_DETECTION_STAGE'] = '1'
os.environ['PHOTOCLEANER_SKIP_HEAVY_DEPS'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tracemalloc
import tempfile
from pathlib import Path

tracemalloc.start()

from photo_cleaner.core.indexer import PhotoIndexer
from photo_cleaner.db.schema import Database

dataset = Path(r'{dataset_path}')

# Use temporary DB for this test
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
    db_path = tmp.name

db = Database(db_path)
indexer = PhotoIndexer(db)

# Index all images - this scans, hashes, and analyzes them
results = indexer.index_folder(dataset)

current, peak = tracemalloc.get_traced_memory()
print(f"RESULT: Indexed {{results.get('processed', 0)}} files, {{peak/(1024*1024):.0f}} MB peak memory")

# Cleanup
import os as os_module
try:
    os_module.remove(db_path)
except:
    pass
"""
        
        logger.info(f"Running duplicate finder on {image_count:,} images...")
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        elapsed = time.time() - start_time
        end_memory_percent = get_memory_percent()
        
        # Calculate metrics
        images_per_second = image_count / elapsed if elapsed > 0 else 0
        mb_per_second = dataset_size_mb / elapsed if elapsed > 0 else 0
        
        # Extract memory from output if available
        peak_memory = 0
        for line in result.stdout.split('\n') + result.stderr.split('\n'):
            if 'peak memory' in line.lower():
                try:
                    peak_memory = float(line.split()[-2])
                except:
                    pass
        
        metrics = {
            'test_name': test_name,
            'timestamp': datetime.now().isoformat(),
            'image_count': image_count,
            'dataset_size_mb': dataset_size_mb,
            'elapsed_seconds': elapsed,
            'elapsed_formatted': format_seconds(elapsed),
            'images_per_second': round(images_per_second, 2),
            'mb_per_second': round(mb_per_second, 2),
            'return_code': result.returncode,
            'memory_usage': {
                'peak_mb': peak_memory if peak_memory > 0 else 0,
                'system_start_percent': start_memory_percent,
                'system_end_percent': end_memory_percent,
                'system_delta_percent': end_memory_percent - start_memory_percent,
            },
            'success': result.returncode == 0,
        }
        
        # Log results
        status = "✅ SUCCESS" if result.returncode == 0 else "❌ FAILED"
        logger.info(f"\n{status}")
        logger.info(f"  Time: {metrics['elapsed_formatted']} ({image_count:,} images)")
        logger.info(f"  Speed: {images_per_second:.1f} images/sec, {mb_per_second:.1f} MB/sec")
        logger.info(f"  Memory: {metrics['memory_usage']['peak_mb']:.0f} MB peak")
        logger.info(f"  System memory: {start_memory_percent:.1f}% → {end_memory_percent:.1f}%")
        
        if result.returncode != 0:
            logger.error(f"STDERR:\n{result.stderr[-500:]}")
        
        return metrics
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ TEST TIMEOUT (exceeded 1 hour)")
        return {
            'test_name': test_name,
            'timestamp': datetime.now().isoformat(),
            'image_count': image_count,
            'dataset_size_mb': dataset_size_mb,
            'error': 'timeout',
            'success': False,
        }
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'test_name': test_name,
            'timestamp': datetime.now().isoformat(),
            'image_count': image_count,
            'dataset_size_mb': dataset_size_mb,
            'error': str(e),
            'success': False,
        }


def format_seconds(seconds: float) -> str:
    """Format seconds into HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_memory_percent() -> float:
    """Get system memory usage percentage."""
    try:
        import psutil
        return psutil.virtual_memory().percent
    except ImportError:
        return 0.0


def save_results(results: list) -> None:
    """Save test results to JSON file."""
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved to: {RESULTS_FILE}")


def load_results() -> list:
    """Load previous test results."""
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE, 'r') as f:
            return json.load(f)
    return []


def main():
    """Main entry point."""
    STRESS_TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("PhotoCleaner Stress Testing Suite")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Test data dir: {STRESS_TEST_DIR}")
    
    results = load_results()
    
    try:
        # Generate 10k dataset
        logger.info("\n" + "="*70)
        logger.info("TASK 1: CREATE 10K DATASET")
        logger.info("="*70)
        dataset_10k = generate_dataset(10000, "10k_images")
        
        # Run 10k test
        logger.info("\n" + "="*70)
        logger.info("TASK 2: TEST 10K DATASET")
        logger.info("="*70)
        result_10k = run_photocleaner_stress_test(dataset_10k, "10k")
        results.append(result_10k)
        save_results(results)
        
        # Generate 50k dataset (optional - may take longer)
        if "--full" in sys.argv or "--50k" in sys.argv:
            logger.info("\n" + "="*70)
            logger.info("TASK 3: CREATE 50K DATASET")
            logger.info("="*70)
            dataset_50k = generate_dataset(50000, "50k_images")
            
            logger.info("\n" + "="*70)
            logger.info("TASK 4: TEST 50K DATASET")
            logger.info("="*70)
            result_50k = run_photocleaner_stress_test(dataset_50k, "50k")
            results.append(result_50k)
            save_results(results)
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("STRESS TEST SUMMARY")
        logger.info("="*70)
        
        for result in results:
            if 'timestamp' in result and result.get('success'):
                logger.info(f"✅ {result['test_name']}: {result['elapsed_formatted']} ({result['images_per_second']} img/sec)")
            elif 'timestamp' in result:
                error = result.get('error', 'unknown error')
                logger.info(f"❌ {result['test_name']}: {error}")
        
        logger.info(f"\nFull results: {RESULTS_FILE}")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        save_results(results)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
