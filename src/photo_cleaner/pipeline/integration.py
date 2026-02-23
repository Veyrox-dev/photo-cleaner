"""
Integration Module: Multiprocessing Pipeline Integration

Provides drop-in replacement for the standard pipeline that uses multiprocessing
for the quality analysis stage (the most expensive operation).

This module patches PhotoCleanerPipeline to use parallel processing when
max_workers > 1 is configured, while maintaining full backward compatibility.

Usage:
    # Enable multiprocessing in existing code
    from photo_cleaner.pipeline.integration import create_parallel_pipeline
    
    pipeline = create_parallel_pipeline(
        db=database,
        config=config,
        use_parallel=True,
        max_workers=None,  # Auto-detect
    )
    
    stats = pipeline.run(folder_path)
"""

import logging
from pathlib import Path
from typing import Optional, Dict
from photo_cleaner.pipeline.pipeline import (
    PhotoCleanerPipeline,
    PipelineConfig,
    PipelineStats,
)
from photo_cleaner.pipeline.parallel_quality_analyzer import ParallelQualityAnalyzer
from photo_cleaner.db.schema import Database

logger = logging.getLogger(__name__)


class ParallelPhotoCleanerPipeline(PhotoCleanerPipeline):
    """
    Extended pipeline that uses multiprocessing for quality analysis.
    
    Inherits all functionality from PhotoCleanerPipeline but overrides
    _stage_quality_analysis to use parallel processing when beneficial.
    
    Maintains full backward compatibility - results are identical to
    single-process version.
    """
    
    def __init__(
        self,
        db: Database,
        config: Optional[PipelineConfig] = None,
        use_parallel: bool = True,
        max_workers: Optional[int] = None,
    ):
        """
        Initialize parallel pipeline.
        
        Args:
            db: Database instance
            config: Pipeline configuration
            use_parallel: Enable multiprocessing for quality analysis
            max_workers: Number of workers (None = auto-detect, 0/1 = single-process)
        """
        super().__init__(db, config)
        
        self.use_parallel = use_parallel
        self.max_workers = max_workers
        
        # Wrap quality analyzer with parallel version
        if use_parallel:
            self.quality_analyzer = ParallelQualityAnalyzer(
                quality_analyzer=self.quality_analyzer,
                scorer=self.scorer,
                cheap_filter=self.cheap_filter,
            )
            logger.info(f"Parallel quality analyzer enabled (max_workers={max_workers})")
    
    def _stage_quality_analysis(self, groups: Dict[str, list]) -> Dict[str, list]:
        """
        Stage 4: Analyze quality with Face Mesh (optional parallelization).
        
        Overrides parent to use parallel analysis when configured.
        
        Args:
            groups: Filtered duplicate groups
            
        Returns:
            Dict mapping group_id to list of QualityResults
        """
        analyzed_groups = {}
        total_images = sum(len(paths) for paths in groups.values())
        
        logger.info(f"Analyzing {total_images} images across {len(groups)} groups")
        
        # Check if we should use parallel processing
        should_use_parallel = (
            self.use_parallel
            and self.max_workers not in (None, 0, 1)
            and total_images > 1
            and isinstance(self.quality_analyzer, ParallelQualityAnalyzer)
        )
        
        if should_use_parallel:
            logger.info(f"Using parallel quality analysis ({self.max_workers} workers)")
            
            # Process all images from all groups in parallel
            all_paths = []
            group_index_map = {}  # Track which group each path belongs to
            
            for group_id, paths in groups.items():
                for path in paths:
                    all_paths.append(path)
                    if group_id not in group_index_map:
                        group_index_map[group_id] = []
                    group_index_map[group_id].append(len(all_paths) - 1)
            
            # Run parallel analysis
            results = self.quality_analyzer.analyze_batch_parallel(
                all_paths,
                max_workers=self.max_workers,
                batch_size=1,
            )
            
            # Re-organize results by group
            for group_id, indices in group_index_map.items():
                group_results = [results[i] for i in indices]
                analyzed_groups[group_id] = group_results
        
        else:
            # Fall back to single-process analysis
            logger.info("Using single-process quality analysis")
            for group_id, paths in groups.items():
                results = self.quality_analyzer.analyze_batch(paths)
                analyzed_groups[group_id] = results
        
        return analyzed_groups


def create_parallel_pipeline(
    db: Database,
    config: Optional[PipelineConfig] = None,
    use_parallel: bool = True,
    max_workers: Optional[int] = None,
) -> PhotoCleanerPipeline:
    """
    Create a pipeline instance with optional parallelization.
    
    Args:
        db: Database instance
        config: Pipeline configuration (uses defaults if None)
        use_parallel: Enable multiprocessing
        max_workers: Number of workers (None = auto-detect)
    
    Returns:
        Pipeline instance (either parallel or standard based on config)
    """
    if use_parallel and max_workers not in (0, 1):
        logger.info("Creating parallel pipeline")
        return ParallelPhotoCleanerPipeline(
            db=db,
            config=config,
            use_parallel=True,
            max_workers=max_workers,
        )
    else:
        logger.info("Creating standard single-process pipeline")
        return PhotoCleanerPipeline(
            db=db,
            config=config,
        )


# ============================================================================
# Quick Integration Hook
# ============================================================================

def enable_parallel_processing(
    pipeline: PhotoCleanerPipeline,
    max_workers: Optional[int] = None,
) -> PhotoCleanerPipeline:
    """
    Enable parallel processing on existing pipeline instance.
    
    This is useful for enabling parallelization in existing code without
    major refactoring.
    
    Args:
        pipeline: Existing PhotoCleanerPipeline instance
        max_workers: Number of workers
    
    Returns:
        New parallel pipeline instance with same database and config
    
    Example:
        # Existing code
        pipeline = PhotoCleanerPipeline(db, config)
        
        # Enable parallelization
        pipeline = enable_parallel_processing(pipeline, max_workers=4)
        
        # Use as normal
        stats = pipeline.run(folder_path)
    """
    return create_parallel_pipeline(
        db=pipeline.db,
        config=pipeline.config,
        use_parallel=True,
        max_workers=max_workers,
    )
