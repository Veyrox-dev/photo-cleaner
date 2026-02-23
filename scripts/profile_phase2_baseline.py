"""
Phase 2 Week 1: Performance Baseline Profiling

Runs comprehensive performance analysis to establish baseline metrics
and identify the Top 5 bottlenecks for optimization.

Usage:
    python scripts/profile_phase2_baseline.py [--test-data PATH] [--output PATH]

Requirements:
    - Test data folder with 1k, 5k, 10k images
    - At least 8GB RAM for 10k image test
    - Results saved to profiling_results/phase2_baseline_YYYYMMDD.json
"""

import argparse
import cProfile
import io
import json
import logging
import pstats
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from photo_cleaner.profiling.profiler import PerformanceProfiler, PerformanceSession
from photo_cleaner.db.schema import Database
from photo_cleaner.pipeline.pipeline import PhotoCleanerPipeline, PipelineConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def profile_pipeline_stage(
    stage_name: str,
    folder_path: Path,
    db_path: Path,
    config: PipelineConfig,
) -> Dict[str, Any]:
    """
    Profile a complete pipeline run with cProfile.
    
    Returns:
        Dict with timing, memory, and bottleneck data
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Profiling: {stage_name}")
    logger.info(f"Folder: {folder_path}")
    logger.info(f"Image count: {len(list(folder_path.glob('**/*.jpg')))} (estimate)")
    logger.info(f"{'='*60}\n")
    
    # Create clean database
    db_path.unlink(missing_ok=True)
    db = Database(db_path)
    db.connect()  # Initialize connection and schema
    
    # Setup profiler
    profiler = cProfile.Profile()
    
    # Run pipeline with profiling
    start_time = time.time()
    start_memory = _get_memory_usage()
    
    profiler.enable()
    try:
        pipeline = PhotoCleanerPipeline(
            db=db,
            config=config
        )
        stats = pipeline.run(folder_path)
    finally:
        profiler.disable()
    
    end_time = time.time()
    end_memory = _get_memory_usage()
    
    # Analyze profiling results
    stream = io.StringIO()
    ps = pstats.Stats(profiler, stream=stream)
    ps.strip_dirs()
    ps.sort_stats('cumulative')
    
    # Get top 20 functions
    ps.print_stats(20)
    profile_output = stream.getvalue()
    
    # Parse top bottlenecks
    bottlenecks = _parse_bottlenecks(ps)
    
    return {
        "stage_name": stage_name,
        "folder_path": str(folder_path),
        "image_count": stats.total_files if hasattr(stats, 'total_files') else 0,
        "duplicate_groups": stats.duplicate_groups if hasattr(stats, 'duplicate_groups') else 0,
        "duration_seconds": end_time - start_time,
        "memory_start_mb": start_memory,
        "memory_peak_mb": end_memory,
        "memory_delta_mb": end_memory - start_memory,
        "top_bottlenecks": bottlenecks[:5],  # Top 5
        "profile_output": profile_output[:2000],  # First 2000 chars
        "timestamp": datetime.now().isoformat(),
    }


def _get_memory_usage() -> float:
    """Get current memory usage in MB."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB
    except ImportError:
        logger.warning("psutil not available, memory tracking disabled")
        return 0.0


def _parse_bottlenecks(ps: pstats.Stats) -> List[Dict[str, Any]]:
    """
    Extract top bottlenecks from pstats.
    
    Returns:
        List of dicts with function name, cumtime, calls, etc.
    """
    bottlenecks = []
    
    # Get stats sorted by cumulative time
    stats = ps.stats
    sorted_stats = sorted(
        stats.items(),
        key=lambda x: x[1][3],  # cumtime
        reverse=True
    )
    
    for (filename, lineno, func_name), (cc, nc, tt, ct, callers) in sorted_stats[:20]:
        bottlenecks.append({
            "function": func_name,
            "file": filename,
            "line": lineno,
            "cumulative_time_s": ct,
            "total_time_s": tt,
            "call_count": nc,
            "time_per_call_ms": (ct / nc * 1000) if nc > 0 else 0,
        })
    
    return bottlenecks


def run_baseline_profiling(
    test_data_root: Path,
    output_dir: Path,
    use_face_mesh: bool = True,
) -> Dict[str, Any]:
    """
    Run complete baseline profiling suite.
    
    Tests:
        - If test_data_root has 1k/, 5k/, 10k/ subfolders: Use those
        - Otherwise: Use test_data_root directly (single folder mode)
    
    Returns:
        Complete profiling results
    """
    results = {
        "profiling_date": datetime.now().isoformat(),
        "phase": "Phase 2 Week 1",
        "goal": "Establish baseline and identify Top 5 bottlenecks",
        "test_runs": []
    }
    
    # Check if subfolders exist (structured mode)
    has_subfolders = (
        (test_data_root / "1k").exists() or
        (test_data_root / "5k").exists() or
        (test_data_root / "10k").exists()
    )
    
    if has_subfolders:
        # Structured mode: 1k, 5k, 10k subfolders
        test_configs = [
            {
                "name": "1k_images_baseline",
                "folder": test_data_root / "1k",
                "db": output_dir / "profile_1k.db",
                "config": PipelineConfig(
                    use_cache=False,  # Cold run
                    use_face_mesh=use_face_mesh,
                    top_n=3,
                )
            },
            {
                "name": "5k_images_medium",
                "folder": test_data_root / "5k",
                "db": output_dir / "profile_5k.db",
                "config": PipelineConfig(
                    use_cache=False,
                    use_face_mesh=use_face_mesh,
                    top_n=3,
                )
            },
            {
                "name": "10k_images_target",
                "folder": test_data_root / "10k",
                "db": output_dir / "profile_10k.db",
                "config": PipelineConfig(
                    use_cache=False,
                    use_face_mesh=use_face_mesh,
                    top_n=3,
                )
            },
            {
                "name": "50k_images_stress",
                "folder": test_data_root / "50k",
                "db": output_dir / "profile_50k.db",
                "config": PipelineConfig(
                    use_cache=False,
                    use_face_mesh=use_face_mesh,
                    top_n=3,
                )
            },
            {
                "name": "100k_images_stress",
                "folder": test_data_root / "100k",
                "db": output_dir / "profile_100k.db",
                "config": PipelineConfig(
                    use_cache=False,
                    use_face_mesh=use_face_mesh,
                    top_n=3,
                )
            },
        ]
    else:
        # Single folder mode: Use test_data_root directly
        logger.info(f"Single folder mode: Using {test_data_root} directly")
        test_configs = [
            {
                "name": f"profile_{test_data_root.name}",
                "folder": test_data_root,
                "db": output_dir / f"profile_{test_data_root.name}.db",
                "config": PipelineConfig(
                    use_cache=False,
                    use_face_mesh=use_face_mesh,
                    top_n=3,
                )
            },
        ]
    
    for test_config in test_configs:
        if not test_config["folder"].exists():
            logger.warning(f"Skipping {test_config['name']}: Folder not found at {test_config['folder']}")
            continue
        
        try:
            result = profile_pipeline_stage(
                stage_name=test_config["name"],
                folder_path=test_config["folder"],
                db_path=test_config["db"],
                config=test_config["config"],
            )
            results["test_runs"].append(result)
            
            # Summary
            logger.info(f"\n✓ {test_config['name']} completed:")
            logger.info(f"  Duration: {result['duration_seconds']:.1f}s")
            logger.info(f"  Memory Delta: {result['memory_delta_mb']:.1f} MB")
            logger.info(f"  Images: {result['image_count']}")
            
        except Exception as e:
            logger.error(f"✗ {test_config['name']} failed: {e}", exc_info=True)
            results["test_runs"].append({
                "stage_name": test_config["name"],
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })
    
    return results


def analyze_bottlenecks(results: Dict[str, Any]) -> None:
    """
    Analyze profiling results and identify Top 5 bottlenecks across all runs.
    
    Prints:
        - Combined Top 5 bottlenecks
        - Optimization recommendations
    """
    logger.info("\n" + "="*60)
    logger.info("BOTTLENECK ANALYSIS")
    logger.info("="*60)
    
    # Aggregate bottlenecks from all runs
    all_bottlenecks = {}
    
    for run in results["test_runs"]:
        if "top_bottlenecks" not in run:
            continue
        
        for bottleneck in run["top_bottlenecks"]:
            func_key = bottleneck["function"]
            
            if func_key not in all_bottlenecks:
                all_bottlenecks[func_key] = {
                    "function": func_key,
                    "total_cumtime": 0,
                    "occurrences": 0,
                    "examples": []
                }
            
            all_bottlenecks[func_key]["total_cumtime"] += bottleneck["cumulative_time_s"]
            all_bottlenecks[func_key]["occurrences"] += 1
            all_bottlenecks[func_key]["examples"].append({
                "run": run["stage_name"],
                "cumtime": bottleneck["cumulative_time_s"],
                "calls": bottleneck["call_count"],
            })
    
    # Sort by total cumulative time
    top_bottlenecks = sorted(
        all_bottlenecks.values(),
        key=lambda x: x["total_cumtime"],
        reverse=True
    )[:5]
    
    logger.info("\nTop 5 Bottlenecks (Aggregated):\n")
    for i, bottleneck in enumerate(top_bottlenecks, 1):
        logger.info(f"{i}. {bottleneck['function']}")
        logger.info(f"   Total Time: {bottleneck['total_cumtime']:.2f}s")
        logger.info(f"   Occurrences: {bottleneck['occurrences']} runs")
        logger.info(f"   Examples:")
        for example in bottleneck["examples"][:2]:
            logger.info(f"     - {example['run']}: {example['cumtime']:.2f}s ({example['calls']} calls)")
        logger.info("")
    
    # Recommendations
    logger.info("\n" + "="*60)
    logger.info("OPTIMIZATION RECOMMENDATIONS")
    logger.info("="*60)
    logger.info("""
Based on profiling results, prioritize optimization in this order:

1. **Image Processing Pipeline**
   - Optimize QualityAnalyzer.analyze_image()
   - Consider batch processing optimizations
   - Review MediaPipe/MTCNN initialization

2. **Database Operations**
   - Check query efficiency (EXPLAIN PLAN)
   - Optimize index usage
   - Batch commits where possible

3. **Cache System**
   - Verify cache hit rates
   - Optimize lookup performance
   - Consider memory vs. disk trade-offs

4. **Duplicate Detection**
   - Review hash calculation efficiency
   - Optimize clustering algorithm

5. **UI Responsiveness**
   - Move heavy operations to background threads
   - Implement progress callbacks
   - Add cancellation support
    """)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 2 Week 1: Performance Baseline Profiling"
    )
    parser.add_argument(
        "--test-data",
        type=Path,
        default=Path("test_data_system"),
        help="Root folder with test data (1k/, 5k/, 10k/ subfolders)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("profiling_results"),
        help="Output directory for results"
    )
    parser.add_argument(
        "--no-face-mesh",
        action="store_true",
        help="Disable MediaPipe Face Mesh for isolation profiling"
    )
    
    args = parser.parse_args()
    
    # Setup output directory
    args.output.mkdir(parents=True, exist_ok=True)
    
    # Run profiling
    logger.info("Starting Phase 2 Week 1 Baseline Profiling...")
    logger.info(f"Test data: {args.test_data}")
    logger.info(f"Output: {args.output}\n")
    
    results = run_baseline_profiling(
        args.test_data,
        args.output,
        use_face_mesh=not args.no_face_mesh,
    )
    
    # Analyze bottlenecks
    analyze_bottlenecks(results)
    
    # Save results
    output_file = args.output / f"phase2_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✓ Profiling complete!")
    logger.info(f"Results saved to: {output_file}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
