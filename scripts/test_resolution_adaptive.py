#!/usr/bin/env python3
"""Test resolution-adaptive optimization"""
import sys
import time
from pathlib import Path

sys.path.insert(0, 'src')

from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer

qa = QualityAnalyzer(None)

# Test on 100 images (mix of sizes)
test_paths = [Path(f'test_data_system/5k/test_img_{i:05d}.jpg') for i in range(1, 101)]

print("Testing resolution-adaptive optimization on 100 images...")
print("-" * 60)

times = []
for path in test_paths:
    start = time.perf_counter()
    result = qa.analyze_image(path)
    elapsed = time.perf_counter() - start
    times.append(elapsed)
    
    if result.error:
        print(f"{path.name}: ERROR - {result.error}")
    else:
        print(f"{path.name}: {elapsed*1000:.1f}ms | {result.width}x{result.height} | Resolution: {result.resolution_score:.1f}MP")

avg_time = sum(times) / len(times) if times else 0
print("-" * 60)
print(f"Average: {avg_time*1000:.1f}ms per image")
print(f"Total: {sum(times):.2f}s for {len(test_paths)} images")
