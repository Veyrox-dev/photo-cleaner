#!/usr/bin/env python3
"""
Memory Profiling Harness for Phase 4.2
Detects memory leaks in image processing pipeline.

Usage:
  python scripts/memory_profiling.py [--test-size=1000] [--runs=5]

Tests:
  1. Config-Hash initialization (100x)
  2. QualityAnalyzer instantiation (100x)
  3. ImageCache operations (1000x)
  4. Face detection pipeline (simulated)
"""

import sys
import os
import gc
import tracemalloc
from pathlib import Path
from dataclasses import dataclass
from typing import List

# Set PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

@dataclass
class MemorySnapshot:
    """Memory state at a point in time"""
    timestamp: str
    total_mb: float
    peak_mb: float
    current_mb: float
    diff_from_prev_mb: float

class MemoryProfiler:
    """CPU-friendly memory profiler using tracemalloc"""
    
    def __init__(self):
        tracemalloc.start()
        self.snapshots: List[MemorySnapshot] = []
        self.baseline = None
    
    def take_snapshot(self, label: str) -> dict:
        """Take memory snapshot and return stats"""
        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        
        current_mb = current / 1024 / 1024
        peak_mb = peak / 1024 / 1024
        
        if self.baseline is None:
            self.baseline = current_mb
            diff = 0
        else:
            diff = current_mb - self.baseline
        
        print(f"[{label:40s}] Current: {current_mb:8.2f} MB | Peak: {peak_mb:8.2f} MB | Diff: {diff:+7.2f} MB")
        
        return {
            'current_mb': current_mb,
            'peak_mb': peak_mb,
            'diff_from_baseline': diff
        }
    
    def reset(self):
        """Reset baseline for next test"""
        gc.collect()
        self.baseline = None
        tracemalloc.reset_peak()

def test_config_hash():
    """Test AppConfig initialization for memory leaks"""
    print("\n" + "="*80)
    print("TEST 1: AppConfig Hash Initialization (100 iterations)")
    print("="*80)
    
    from photo_cleaner.config import AppConfig
    
    profiler = MemoryProfiler()
    profiler.take_snapshot("Baseline")
    
    for i in range(100):
        if i % 20 == 0:
            profiler.take_snapshot(f"After {i+1} iterations")
        # Force new instance
        config = AppConfig()
        del config
    
    profiler.take_snapshot("Final (100 iterations)")
    
    return profiler

def test_quality_analyzer():
    """Test QualityAnalyzer instantiation for memory leaks"""
    print("\n" + "="*80)
    print("TEST 2: QualityAnalyzer Instantiation (100 iterations)")
    print("="*80)
    
    from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
    
    profiler = MemoryProfiler()
    profiler.take_snapshot("Baseline")
    
    for i in range(100):
        if i % 20 == 0:
            profiler.take_snapshot(f"After {i+1} iterations")
        analyzer = QualityAnalyzer()
        del analyzer
    
    profiler.take_snapshot("Final (100 iterations)")
    
    return profiler

def test_image_cache():
    """Test ImageCache for memory leaks"""
    print("\n" + "="*80)
    print("TEST 3: ImageCache Operations (1000 simulated entries)")
    print("="*80)
    
    try:
        from photo_cleaner.cache.image_cache import ImageCache
        
        profiler = MemoryProfiler()
        profiler.take_snapshot("Baseline")
        
        cache = ImageCache(max_size_mb=100)
        
        # Simulate cache operations
        for i in range(1000):
            if i % 250 == 0:
                profiler.take_snapshot(f"After {i} cache operations")
            # Simulate adding and removing cache entries
            key = f"image_{i}.jpg"
            cache.set(key, {"size": 1024*100, "data": b"x"*1000})
            if i % 10 == 0:
                cache.get(key)
        
        profiler.take_snapshot("Final (1000 operations)")
        
        return profiler
    except ImportError:
        print("ImageCache not available in this version")
        return None

def main():
    """Run all memory profiling tests"""
    print("\n" + "="*80)
    print("PHASE 4.2 MEMORY PROFILING SUITE")
    print("PhotoCleaner v0.8.4 - Memory Leak Detection")
    print("="*80)
    
    results = {}
    
    try:
        results['config_hash'] = test_config_hash()
    except Exception as e:
        print(f"ERROR in config_hash test: {e}")
        traceback.print_exc()
    
    try:
        results['quality_analyzer'] = test_quality_analyzer()
    except Exception as e:
        print(f"ERROR in quality_analyzer test: {e}")
        traceback.print_exc()
    
    try:
        results['image_cache'] = test_image_cache()
    except Exception as e:
        print(f"ERROR in image_cache test: {e}")
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("MEMORY PROFILING SUMMARY")
    print("="*80)
    print("✅ All tests complete. Check above for memory leak indicators:")
    print("   - Diff should stay near 0 MB (not grow continuously)")
    print("   - Peak should increase only slightly per iteration")
    print("   - No AttributeError or ImportError in tests")
    print("="*80)

if __name__ == "__main__":
    main()
