#!/usr/bin/env python3
"""
Simple stress test: measure time to scan/hash 10k images.
"""

import sys
import os
import time
import tracemalloc
from pathlib import Path

# Setup
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
os.environ['PHOTOCLEANER_FACE_DETECTOR'] = 'haar'
os.environ['PHOTOCLEANER_EYE_DETECTION_STAGE'] = '1'
os.environ['PHOTOCLEANER_SKIP_HEAVY_DEPS'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from photo_cleaner.io.file_scanner import FileScanner
from photo_cleaner.core.hasher import ImageHasher

def stress_test_10k():
    """Run stress test on 10k image dataset."""
    dataset_dir = Path(__file__).parent.parent / "stress_test_datasets" / "10k_images"
    
    if not dataset_dir.exists():
        print(f"❌ Dataset not found: {dataset_dir}")
        print("   Run: python scripts/stress_test_images.py to generate dataset first")
        sys.exit(1)
    
    # Count images
    image_files = list(dataset_dir.rglob("*.jpg")) + list(dataset_dir.rglob("*.heic"))
    print(f"Found {len(image_files):,} images in {dataset_dir}")
    
    # Trace memory
    tracemalloc.start()
    start_time = time.time()
    start_mem = tracemalloc.get_traced_memory()[0]
    
    # Test 1: File scanning (simulates discovery phase)
    scanner = FileScanner(dataset_dir)
    files = list(scanner.scan())
    scan_time = time.time() - start_time
    
    print(f"\n✅ SCAN PHASE")
    print(f"   Found {len(files):,} files in {scan_time:.2f}s")
    print(f"   Speed: {len(files)/scan_time:.0f} files/sec")
    
    # Test 2: Image hashing (CPU-intensive)
    hasher = ImageHasher()
    hash_start = time.time()
    hash_count = 0
    hash_errors = 0
    
    for file_path in files[:100]:  # Hash first 100 to keep test quick
        try:
            result = hasher.hash_file(file_path)
            if result:
                hash_count += 1
        except Exception as e:
            hash_errors += 1
    
    hash_time = time.time() - hash_start
    current, peak = tracemalloc.get_traced_memory()
    
    print(f"\n✅ HASH SAMPLE (100 files)")
    print(f"   Successfully hashed {hash_count} files in {hash_time:.2f}s")
    print(f"   Errors: {hash_errors}")
    if hash_count > 0:
        print(f"   Speed: {hash_count/hash_time:.0f} files/sec")
    
    # Memory report
    mem_used = (current - start_mem) / (1024 * 1024)
    peak_mb = peak / (1024 * 1024)
    
    print(f"\n📊 MEMORY USAGE")
    print(f"   Current: {current / (1024 * 1024):.0f} MB")
    print(f"   Delta since start: {mem_used:+.0f} MB")
    print(f"   Peak: {peak_mb:.0f} MB")
    
    # Extrapolate
    total_time = time.time() - start_time
    if hash_count > 0:
        extrapolated_time = (len(files) / hash_count) * hash_time
        print(f"\n📈 EXTRAPOLATION (all {len(files):,} files)")
        print(f"   Estimated time: {extrapolated_time/60:.1f} minutes")
        print(f"   Estimated speed: {len(files)/extrapolated_time:.0f} files/sec")
    
    print(f"\nTotal test time: {total_time:.2f}s")
    
    tracemalloc.stop()

if __name__ == "__main__":
    stress_test_10k()
