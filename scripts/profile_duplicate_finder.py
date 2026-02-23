#!/usr/bin/env python3
"""
Profile Duplicate Detection Pipeline

Measures execution time for hash-based duplicate grouping.

Usage:
    python scripts/profile_duplicate_finder.py --output results/duplicate_profile_5k.json
"""

import argparse
import json
import os
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class DuplicateProfileMetric:
    """Single stage measurement"""
    stage: str
    duration_seconds: float
    duplicate_groups_found: int
    images_in_groups: int


class DuplicateFinderProfiler:
    """Profile duplicate finder performance"""
    
    def __init__(self, db_path: str = "photo_cleaner.db"):
        self.db_path = db_path
        self.metrics: List[DuplicateProfileMetric] = []
        
    def profile_full_pipeline(self) -> Dict:
        """Profile duplicate detection pipeline"""
        
        # Check database exists
        if not os.path.exists(self.db_path):
            print(f"⚠️  Database not found: {self.db_path}")
            print("   Run indexing first to create database")
            return None
        
        # Get indexed files
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files")
        image_count = cursor.fetchone()[0]
        
        if image_count == 0:
            print("⚠️  No indexed files in database")
            conn.close()
            return None
        
        print(f"🔍 Profiling duplicate detection for {image_count} images")
        print("-" * 60)
        
        start_time = time.perf_counter()
        
        # Stage 1: Load file records
        print("📊 Stage 1: Loading file records...")
        stage_start = time.perf_counter()
        
        cursor.execute("SELECT file_id, path, file_hash FROM files")
        files = cursor.fetchall()
        
        stage_duration = time.perf_counter() - stage_start
        self.metrics.append(DuplicateProfileMetric(
            stage="load_files",
            duration_seconds=stage_duration,
            duplicate_groups_found=0,
            images_in_groups=0
        ))
        print(f"   ✓ Loaded {image_count} files in {stage_duration:.2f}s")
        
        # Stage 2: Hash-based grouping
        print("📊 Stage 2: Hash-based grouping (exact duplicates)...")
        stage_start = time.perf_counter()
        
        hash_groups = defaultdict(list)
        for file_id, path, file_hash in files:
            if file_hash:
                hash_groups[file_hash].append((file_id, path))
        
        stage_duration = time.perf_counter() - stage_start
        exact_dup_count = sum(1 for g in hash_groups.values() if len(g) > 1)
        exact_dup_images = sum(len(g) for g in hash_groups.values() if len(g) > 1)
        
        self.metrics.append(DuplicateProfileMetric(
            stage="exact_duplicates",
            duration_seconds=stage_duration,
            duplicate_groups_found=exact_dup_count,
            images_in_groups=exact_dup_images
        ))
        print(f"   ✓ Found {exact_dup_count} exact duplicate groups in {stage_duration:.2f}s")
        print(f"     ({exact_dup_images} images involved)")
        
        conn.close()
        
        # Total time
        total_duration = time.perf_counter() - start_time
        
        # Results
        result = {
            "profile_type": "duplicate_finder",
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "image_count": image_count,
            
            "timing": {
                "total_duration_seconds": total_duration,
                "per_image_avg_ms": (total_duration / image_count * 1000) if image_count > 0 else 0
            },
            
            "duplicates_found": {
                "exact_duplicate_groups": exact_dup_count,
                "exact_duplicate_images": exact_dup_images,
                "total_duplicate_images": exact_dup_images
            },
            
            "performance_classification": self._classify_performance(
                total_duration / image_count if image_count > 0 else 0
            ),
            
            "stage_breakdown": [asdict(m) for m in self.metrics]
        }
        
        return result
    
    def _classify_performance(self, avg_time_seconds: float) -> str:
        """Classify performance level"""
        ms = avg_time_seconds * 1000
        
        if ms < 1:
            return "EXCELLENT"
        elif ms < 5:
            return "GOOD"
        elif ms < 20:
            return "ACCEPTABLE"
        elif ms < 50:
            return "SLOW"
        else:
            return "VERY_SLOW"


def main():
    parser = argparse.ArgumentParser(
        description="Profile Duplicate Detection Pipeline"
    )
    parser.add_argument(
        "--db",
        default="photo_cleaner.db",
        help="Path to database file (default: photo_cleaner.db)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file for results"
    )
    
    args = parser.parse_args()
    
    # Run profiling
    try:
        profiler = DuplicateFinderProfiler(args.db)
        results = profiler.profile_full_pipeline()
        
        if results is None:
            return 1
        
        # Save results
        from pathlib import Path
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n" + "=" * 60)
        print("✅ Profile Complete")
        print("=" * 60)
        print(f"Images analyzed: {results['image_count']}")
        print(f"Total duration: {results['timing']['total_duration_seconds']:.2f}s")
        print(f"Per-image average: {results['timing']['per_image_avg_ms']:.2f}ms")
        print(f"Duplicates found: {results['duplicates_found']['total_duplicate_images']}")
        print(f"Performance: {results['performance_classification']}")
        print(f"Results saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=__import__('sys').stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
