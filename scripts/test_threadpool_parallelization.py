#!/usr/bin/env python3
"""
Test ThreadPool parallelization for QualityAnalyzer.

Compare sequential vs parallel performance.
"""
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer


def test_sequential(analyzer, test_images, max_test=None):
    """Test sequential analysis (old approach)."""
    paths = test_images[:max_test] if max_test else test_images
    
    print(f"\n[SEQ] SEQUENTIAL TEST ({len(paths)} images)")
    print("=" * 60)
    
    start = time.perf_counter()
    results = []
    
    for i, path in enumerate(paths):
        result = analyzer.analyze_image(path)
        results.append(result)
        
        if (i + 1) % 10 == 0:
            elapsed = time.perf_counter() - start
            per_img = elapsed / (i + 1)
            print(f"  {i + 1}/{len(paths)} images | "
                  f"{elapsed:.2f}s | {per_img*1000:.1f}ms/img")
    
    total_time = time.perf_counter() - start
    per_image = total_time / len(paths)
    
    print(f"\nOK Sequential Results:")
    print(f"  Total Time: {total_time:.2f}s")
    print(f"  Per Image: {per_image*1000:.1f}ms")
    print(f"  Successful: {sum(1 for r in results if r.error is None)}/{len(results)}")
    
    return total_time, per_image, results


def test_parallel(analyzer, test_images, max_workers=4, max_test=None):
    """Test parallel analysis (new ThreadPool approach)."""
    paths = test_images[:max_test] if max_test else test_images
    
    print(f"\n[PAR] PARALLEL TEST ({len(paths)} images, {max_workers} workers)")
    print("=" * 60)
    
    start = time.perf_counter()
    results = [None] * len(paths)
    processed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(analyzer.analyze_image, path): idx
            for idx, path in enumerate(paths)
        }
        
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                result = future.result()
                results[idx] = result
                processed += 1
            except Exception as e:
                print(f"  ❌ Error analyzing {paths[idx]}: {e}")
                results[idx] = None
                processed += 1
            
            if processed % 10 == 0:
                elapsed = time.perf_counter() - start
                per_img = elapsed / processed
                print(f"  {processed}/{len(paths)} images | "
                      f"{elapsed:.2f}s | {per_img*1000:.1f}ms/img")
    
    total_time = time.perf_counter() - start
    per_image = total_time / len(paths)
    
    print(f"\nOK Parallel Results:")
    print(f"  Total Time: {total_time:.2f}s")
    print(f"  Per Image: {per_image*1000:.1f}ms")
    print(f"  Successful: {sum(1 for r in results if r and r.error is None)}/{len(results)}")
    
    return total_time, per_image, results


def main():
    """Main test function."""
    # Get test images
    test_data_dir = Path(__file__).parent.parent / "test_data_system" / "5k"
    if not test_data_dir.exists():
        test_data_dir = Path(__file__).parent.parent / "test_data_system" / "1k"
    
    if not test_data_dir.exists():
        print("ERROR: test_data_system directory not found!")
        return
    
    test_images = sorted([p for p in test_data_dir.glob("*.jpg") if p.is_file()])
    
    if not test_images:
        print("ERROR: No test images found!")
        return
    
    print(f"Found {len(test_images)} test images")
    print(f"   Directory: {test_data_dir}")
    
    # Create analyzer
    print("\nInitializing QualityAnalyzer...")
    analyzer = QualityAnalyzer(use_face_mesh=False)
    print("QualityAnalyzer initialized")
    
    # Test with limited images first (100 for speed)
    max_test = min(100, len(test_images))
    
    print(f"\nRunning benchmark with {max_test} images...")
    
    # Sequential test
    seq_time, seq_per_img, seq_results = test_sequential(analyzer, test_images, max_test)
    
    # Parallel test (4 workers)
    par_time_4, par_per_img_4, par_results_4 = test_parallel(
        analyzer, test_images, max_workers=4, max_test=max_test
    )
    
    # Parallel test (8 workers)
    par_time_8, par_per_img_8, par_results_8 = test_parallel(
        analyzer, test_images, max_workers=8, max_test=max_test
    )
    
    # Calculate speedups
    speedup_4 = seq_time / par_time_4
    speedup_8 = seq_time / par_time_8
    per_img_speedup_4 = seq_per_img / par_per_img_4
    per_img_speedup_8 = seq_per_img / par_per_img_8
    
    print("\n" + "=" * 60)
    print("SPEEDUP COMPARISON")
    print("=" * 60)
    print(f"Sequential Time:     {seq_time:.2f}s ({seq_per_img*1000:.1f}ms/img)")
    print(f"Parallel (4 workers): {par_time_4:.2f}s ({par_per_img_4*1000:.1f}ms/img) - {speedup_4:.2f}x")
    print(f"Parallel (8 workers): {par_time_8:.2f}s ({par_per_img_8*1000:.1f}ms/img) - {speedup_8:.2f}x")
    
    best_time = min(par_time_4, par_time_8)
    best_workers = 4 if par_time_4 < par_time_8 else 8
    best_speedup = seq_time / best_time
    
    if best_speedup >= 3.0:
        print(f"RESULT: Excellent - {best_workers} workers achieved {best_speedup:.2f}x speedup!")
    elif best_speedup >= 2.0:
        print(f"RESULT: Good - {best_workers} workers achieved {best_speedup:.2f}x speedup!")
    elif best_speedup >= 1.5:
        print(f"RESULT: Fair - {best_workers} workers achieved {best_speedup:.2f}x speedup")
    else:
        print(f"RESULT: Limited speedup - {best_speedup:.2f}x (threading overhead)")
    
    # Projected 5k performance
    print("\n" + "=" * 60)
    print("PROJECTED 5000 IMAGE PERFORMANCE")
    print("=" * 60)
    seq_5k = seq_per_img * 5000
    par_5k_4 = par_per_img_4 * 5000
    par_5k_8 = par_per_img_8 * 5000
    
    par_5k = min(par_5k_4, par_5k_8)
    print(f"Sequential:  {seq_5k:.1f}s ({seq_5k/60:.1f} minutes)")
    print(f"Parallel 4:  {par_5k_4:.1f}s ({par_5k_4/60:.1f} minutes) - {seq_5k/par_5k_4:.2f}x")
    print(f"Parallel 8:  {par_5k_8:.1f}s ({par_5k_8/60:.1f} minutes) - {seq_5k/par_5k_8:.2f}x")
    
    # With resolution-adaptive processing
    baseline_5k = 228.9 * 5000 / 1000  # 228.9ms per image was baseline
    total_speedup = baseline_5k / par_5k
    print(f"\nCombined with Resolution-Adaptive Processing:")
    print(f"Baseline (228.9ms/img): {baseline_5k:.1f}s")
    print(f"With ThreadPool:        {par_5k:.1f}s")
    print(f"Total Speedup:          {total_speedup:.2f}x from baseline!")


if __name__ == "__main__":
    main()
