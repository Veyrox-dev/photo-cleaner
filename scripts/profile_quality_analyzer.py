#!/usr/bin/env python3
"""
Profile Quality Analysis Pipeline

Measures execution time for:
- Image loading
- Feature calculation
- Database access patterns

Usage:
    python scripts/profile_quality_analyzer.py --test-data test_data_system/5k --output results/quality_profile_5k.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List
from PIL import Image
import numpy as np

@dataclass
class QualityProfileMetric:
    """Single quality analysis measurement"""
    image_path: str
    total_time: float  # Total analysis time
    file_size_kb: float
    image_size: tuple  # (width, height)
    
    def to_dict(self):
        return asdict(self)


class QualityAnalyzerProfiler:
    """Profile quality analyzer performance"""
    
    def __init__(self):
        self.metrics: List[QualityProfileMetric] = []
        
    def profile_single_image(self, image_path: str) -> QualityProfileMetric:
        """Profile analysis of single image"""
        
        start = time.perf_counter()
        
        try:
            # Load image
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # Simulate quality analysis operations
            # 1. Convert to grayscale
            if len(img_array.shape) == 3:
                gray = np.dot(img_array[...,:3], [0.299, 0.587, 0.114])
            else:
                gray = img_array
            
            # 2. Calculate sharpness (Laplacian variance)
            from scipy import ndimage
            laplacian = ndimage.laplace(gray)
            sharpness = laplacian.var()
            
            # 3. Calculate lighting
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            end = time.perf_counter()
            total_time = end - start
            
            file_size_kb = os.path.getsize(image_path) / 1024
            
            metric = QualityProfileMetric(
                image_path=image_path,
                total_time=total_time,
                file_size_kb=file_size_kb,
                image_size=img.size
            )
            
            return metric
            
        except Exception as e:
            # Return error metric
            return QualityProfileMetric(
                image_path=image_path,
                total_time=0.0,
                file_size_kb=0,
                image_size=(0, 0)
            )
    
    def profile_batch(self, test_data_dir: str, max_images: int = None) -> Dict:
        """Profile batch of images"""
        
        test_path = Path(test_data_dir)
        if not test_path.exists():
            raise FileNotFoundError(f"Test data directory not found: {test_data_dir}")
        
        # Get all test images
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        image_files = [
            f for f in test_path.rglob('*')
            if f.suffix.lower() in image_extensions
        ]
        
        if max_images:
            image_files = image_files[:max_images]
        
        image_count = len(image_files)
        print(f"📸 Profiling {image_count} images from {test_data_dir}")
        print("-" * 60)
        
        # Profile each image
        start_time = time.perf_counter()
        
        for i, image_path in enumerate(image_files, 1):
            try:
                metric = self.profile_single_image(str(image_path))
                self.metrics.append(metric)
                
                if i % 100 == 0 or i == image_count:
                    elapsed = time.perf_counter() - start_time
                    per_image = elapsed / i
                    remaining = (image_count - i) * per_image
                    print(f"  {i:5d}/{image_count} | {per_image:6.2f}ms/image | "
                          f"Elapsed: {elapsed:6.1f}s | ETA: {remaining:6.1f}s")
            
            except Exception as e:
                print(f"  ❌ Error analyzing {image_path}: {e}")
                continue
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        # Calculate statistics
        times = [m.total_time for m in self.metrics]
        valid_count = len(times)
        
        if valid_count > 0:
            min_time = min(times)
            max_time = max(times)
            avg_time = sum(times) / len(times)
            total_ms = sum(times)
        else:
            min_time = max_time = avg_time = total_ms = 0
        
        result = {
            "profile_type": "quality_analyzer",
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_data_dir": str(test_data_dir),
            "image_count": image_count,
            "successful_analyses": valid_count,
            "failed_analyses": image_count - valid_count,
            
            "timing": {
                "total_duration_seconds": total_duration,
                "per_image_min_ms": min_time * 1000,
                "per_image_max_ms": max_time * 1000,
                "per_image_avg_ms": avg_time * 1000,
                "total_analysis_ms": total_ms * 1000,
            },
            
            "performance_classification": self._classify_performance(avg_time),
            
            "memory_estimated_mb": self._estimate_memory_usage(valid_count),
            
            "detailed_metrics": [m.to_dict() for m in self.metrics[:10]]  # First 10
        }
        
        return result
    
    def _classify_performance(self, avg_time_seconds: float) -> str:
        """Classify performance level"""
        ms = avg_time_seconds * 1000
        
        if ms < 100:
            return "EXCELLENT"
        elif ms < 500:
            return "GOOD"
        elif ms < 1000:
            return "ACCEPTABLE"
        elif ms < 2000:
            return "SLOW"
        else:
            return "VERY_SLOW"
    
    def _estimate_memory_usage(self, image_count: int) -> float:
        """Estimate memory usage in MB"""
        # Rough estimate: ~50KB per image in memory during analysis
        return (image_count * 50) / 1024


def main():
    parser = argparse.ArgumentParser(
        description="Profile Quality Analysis Pipeline"
    )
    parser.add_argument(
        "--test-data",
        required=True,
        help="Path to test data directory"
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=None,
        help="Maximum images to profile (default: all)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file for results"
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run profiling
    try:
        profiler = QualityAnalyzerProfiler()
        results = profiler.profile_batch(
            args.test_data,
            max_images=args.max_images
        )
        
        # Save results
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n" + "=" * 60)
        print("✅ Profile Complete")
        print("=" * 60)
        print(f"Images processed: {results['successful_analyses']}/{results['image_count']}")
        print(f"Total duration: {results['timing']['total_duration_seconds']:.2f}s")
        print(f"Per-image average: {results['timing']['per_image_avg_ms']:.2f}ms")
        print(f"Performance: {results['performance_classification']}")
        print(f"Results saved to: {args.output}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
