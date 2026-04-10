"""
Final PhotoCleaner Pipeline

Optimized pipeline for photo cleanup with minimal AI overhead.

Pipeline stages:
1. Index - Fast local hashing and metadata extraction
2. Find duplicates - Hamming distance ≤ threshold
3. Cheap filter - Fast quality filters without AI
4. Quality analysis - MediaPipe Face Mesh on duplicate groups only
5. Score and rank - Mark top N to keep, rest to delete
6. User decision - UI shows results for final confirmation
"""

import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from photo_cleaner.cache.image_cache_manager import ImageCacheManager
from photo_cleaner.core.hasher import hamming_distance
from photo_cleaner.core.indexer import PhotoIndexer
from photo_cleaner.db.schema import Database
from photo_cleaner.duplicates.finder import DuplicateFinder
from photo_cleaner.models.status import FileStatus
from photo_cleaner.pipeline.cheap_filter import CheapFilter
from photo_cleaner.pipeline.parallel_quality_analyzer import ParallelQualityAnalyzer
from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
from photo_cleaner.pipeline.scorer import GroupScorer
from photo_cleaner.repositories.file_repository import FileRepository

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    
    # Duplicate detection
    hash_distance_threshold: int = 5
    
    # Cheap filter thresholds
    min_width: int = 800
    min_height: int = 600
    sharpness_threshold: float = 50.0
    brightness_low: float = 30.0
    brightness_high: float = 225.0
    
    # Quality analysis
    use_face_mesh: bool = True
    min_detection_confidence: float = 0.5
    
    # Scoring
    top_n: int = 3
    
    # Cache system
    use_cache: bool = True
    force_reanalyze: bool = False
    
    # Performance
    max_workers: Optional[int] = None
    skip_existing_index: bool = True
    
    def __post_init__(self):
        """P2.1: Validate pipeline configuration parameters."""
        # Validate hash distance threshold
        if not (0 <= self.hash_distance_threshold <= 32):
            raise ValueError(
                f"hash_distance_threshold must be 0-32, got {self.hash_distance_threshold}"
            )
        
        # Validate thresholds
        if self.sharpness_threshold < 0:
            raise ValueError(f"sharpness_threshold must be >= 0, got {self.sharpness_threshold}")
        
        if not (0 <= self.brightness_low < self.brightness_high <= 255):
            raise ValueError(
                f"brightness must be ordered 0 <= {self.brightness_low} < "
                f"{self.brightness_high} <= 255"
            )
        
        # P6.7: Ensure max_workers is at least 1
        if self.max_workers is not None and self.max_workers < 1:
            logger.warning(
                f"max_workers={self.max_workers} is invalid, using default"
            )
            self.max_workers = None


@dataclass
class PipelineStats:
    """Statistics from pipeline execution."""
    
    # Indexing
    indexed_files: int = 0
    skipped_files: int = 0
    failed_index: int = 0
    
    # Duplicate detection
    duplicate_groups: int = 0
    total_duplicates: int = 0
    
    # Cheap filter
    passed_filter: int = 0
    failed_filter: int = 0
    
    # Quality analysis
    analyzed_files: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Scoring
    marked_keep: int = 0
    marked_delete: int = 0
    skipped_locked: int = 0


class PhotoCleanerPipeline:
    """
    Main pipeline orchestrator for PhotoCleaner.
    
    Coordinates all stages from indexing to final scoring.
    """
    
    def __init__(
        self,
        db: Database,
        config: Optional[PipelineConfig] = None,
    ):
        """
        Initialize pipeline.
        
        Args:
            db: Database instance
            config: Pipeline configuration (uses defaults if None)
        """
        self.db = db
        self.config = config or PipelineConfig()
        
        # Initialize components
        self.indexer = PhotoIndexer(db, max_workers=self.config.max_workers)
        self.finder = DuplicateFinder(db, phash_threshold=self.config.hash_distance_threshold)
        self.cheap_filter = CheapFilter(
            min_width=self.config.min_width,
            min_height=self.config.min_height,
            sharpness_threshold=self.config.sharpness_threshold,
            brightness_low=self.config.brightness_low,
            brightness_high=self.config.brightness_high,
        )
        self.quality_analyzer = QualityAnalyzer(
            use_face_mesh=self.config.use_face_mesh,
            min_detection_confidence=self.config.min_detection_confidence,
        )
        self.scorer = GroupScorer(top_n=self.config.top_n)
        self._use_process_parallel = os.getenv("PHOTOCLEANER_USE_PROCESS_PARALLEL", "0").lower() in ("1", "true", "yes")
        self._parallel_quality_analyzer: Optional[ParallelQualityAnalyzer] = None
        if self._use_process_parallel:
            self._parallel_quality_analyzer = ParallelQualityAnalyzer(self.quality_analyzer, scorer=self.scorer)
        
        # Initialize cache manager
        self.cache_manager = ImageCacheManager(db.conn) if self.config.use_cache else None
        # File repository
        self.file_repo = FileRepository(db.conn)
        
        # PHASE 4 FIX 1: Initialize CameraCalibrator for ML learning
        from photo_cleaner.pipeline.camera_calibrator import CameraCalibrator
        self.camera_calibrator = CameraCalibrator(db.conn)
        
        # Statistics
        self.stats = PipelineStats()
    
    def run(self, folder_path: Path) -> PipelineStats:
        """
        Run complete pipeline on a folder.
        
        Args:
            folder_path: Root folder to process
            
        Returns:
            Pipeline statistics
        """
        logger.info(f"Starting pipeline on {folder_path}")

        # Enforce FREE quota before indexing (server-backed usage)
        if os.environ.get("PHOTOCLEANER_SKIP_FREE_QUOTA", "0").lower() in ("1", "true", "yes"):
            logger.warning("FREE quota check bypassed via PHOTOCLEANER_SKIP_FREE_QUOTA (profiling/test mode)")
        else:
            try:
                from photo_cleaner.license import get_license_manager
                from photo_cleaner.io.file_scanner import FileScanner

                license_mgr = get_license_manager()
                total_files = FileScanner(folder_path).count_files()
                allowed, reason = license_mgr.check_and_consume_free_images(total_files)
                if not allowed:
                    raise ValueError(reason or "Free-Limit erreicht. Bitte Upgrade auf PRO.")
            except (ImportError, AttributeError) as e:
                logger.warning("License check skipped: %s", e)
        
        # Stage 1: Index
        logger.info("Stage 1: Indexing files...")
        index_stats = self._stage_index(folder_path)
        self.stats.indexed_files = index_stats["processed"]
        self.stats.skipped_files = index_stats["skipped"]
        self.stats.failed_index = index_stats["failed"]
        
        if self.stats.indexed_files == 0 and self.stats.skipped_files == 0:
            logger.warning("No files indexed, aborting pipeline")
            return self.stats
        
        # Stage 2: Find duplicates
        logger.info("Stage 2: Finding duplicate groups...")
        duplicate_groups = self._stage_find_duplicates()
        self.stats.duplicate_groups = len(duplicate_groups)
        self.stats.total_duplicates = sum(len(group) for group in duplicate_groups.values())

        # NEW: Mark standalone images (no duplicate group) as KEEP so they don't block UI progress
        self._mark_single_images_keep()
        
        if not duplicate_groups:
            logger.info("No duplicates found, pipeline complete")
            return self.stats
        
        logger.info(
            f"Found {self.stats.duplicate_groups} groups with "
            f"{self.stats.total_duplicates} total images"
        )
        
        # Stage 3: Cheap filter
        logger.info("Stage 3: Applying cheap filters...")
        filtered_groups = self._stage_cheap_filter(duplicate_groups)
        
        # Stage 4: Quality analysis (only on filtered groups)
        logger.info("Stage 4: Analyzing quality with Face Mesh...")
        analyzed_groups = self._stage_quality_analysis(filtered_groups)
        self.stats.analyzed_files = sum(len(results) for results in analyzed_groups.values())
        
        # Stage 5: Score and mark
        logger.info("Stage 5: Scoring and marking images...")
        score_stats = self._stage_score_and_mark(analyzed_groups)
        self.stats.marked_keep = score_stats["marked_keep"]
        self.stats.marked_delete = score_stats["marked_delete"]
        self.stats.skipped_locked = score_stats["skipped_locked"]
        
        logger.info("Pipeline complete!")
        self._log_stats()
        
        return self.stats
    
    def _stage_index(self, folder_path: Path) -> dict[str, int]:
        """
        Stage 1: Index all files in folder.
        
        Returns:
            Indexing statistics
        """
        return self.indexer.index_folder(
            folder_path,
            skip_existing=self.config.skip_existing_index,
        )
    
    def _stage_find_duplicates(self) -> dict[str, list[Path]]:
        """
        Stage 2: Find duplicate groups using perceptual hash.
        
        OPTIMIZED: Uses hash-bucket algorithm instead of O(n²) full comparison.
        Performance gain: x5-x10 for large datasets.
        
        Returns:
            Dict mapping group_id to list of file paths
        """
        from collections import defaultdict
        
        # Get all files with phash
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT file_id, path, phash
            FROM files
            WHERE phash IS NOT NULL
            """
        )
        files = cursor.fetchall()
        
        if not files:
            return {}
        
        logger.info(f"Finding duplicates for {len(files)} files using optimized bucket algorithm...")
        
        # OPTIMIZATION: Group files into hash buckets (first 8 bits)
        # Only compare files within same bucket → reduces comparisons by ~256x
        buckets = defaultdict(list)
        for file_row in files:
            phash = file_row["phash"]
            if phash and len(phash) >= 8:
                bucket_key = phash[:8]  # First 8 bits as bucket key
                buckets[bucket_key].append(file_row)
        
        logger.debug(f"Created {len(buckets)} hash buckets")
        
        # Find duplicates within each bucket
        groups: dict[str, list[Path]] = {}
        processed = set()
        group_counter = 0
        total_comparisons = 0
        
        for bucket_key, bucket_files in buckets.items():
            # Skip buckets with only 1 file
            if len(bucket_files) <= 1:
                continue
            
            # Compare files within bucket
            for i, file_a in enumerate(bucket_files):
                if file_a["file_id"] in processed:
                    continue
                
                group = [Path(file_a["path"])]
                group_ids = {file_a["file_id"]}
                
                for file_b in bucket_files[i + 1:]:
                    if file_b["file_id"] in processed:
                        continue
                    
                    try:
                        distance = hamming_distance(file_a["phash"], file_b["phash"])
                        total_comparisons += 1
                        
                        if distance <= self.config.hash_distance_threshold:
                            group.append(Path(file_b["path"]))
                            group_ids.add(file_b["file_id"])
                            processed.add(file_b["file_id"])
                            
                    except Exception as e:
                        logger.warning(f"Failed to compare hashes: {e}")
                        continue
                
                # Only create group if we found duplicates
                if len(group) > 1:
                    group_id = str(uuid.uuid4())[:8]
                    groups[group_id] = group
                    processed.update(group_ids)
                    group_counter += 1
                    
                    # Store in duplicates table
                    self._store_duplicate_group(group_id, group)
        
        # Log optimization effectiveness
        naive_comparisons = (len(files) * (len(files) - 1)) // 2
        if naive_comparisons > 0 and total_comparisons > 0:
            speedup = naive_comparisons / total_comparisons
            logger.info(
                f"Bucket optimization: {total_comparisons} comparisons "
                f"vs {naive_comparisons} naive (x{speedup:.1f} speedup)"
            )
        
        return groups

    def _mark_single_images_keep(self) -> None:
        """Mark images that are not part of any duplicate group as KEEP.

        Rationale:
        - Single images are not shown in the duplicate review UI but still count as "undecided" if left null/undecided.
        - Marking them KEEP upfront prevents progress from being blocked and matches expected default behavior.
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT f.path
                FROM files f
                LEFT JOIN duplicates d ON f.file_id = d.file_id
                WHERE d.file_id IS NULL
                  AND f.is_deleted = 0
                  AND (f.file_status IS NULL OR f.file_status IN ('UNDECIDED', 'UNSURE'))
                """
            )
            single_paths = [Path(row[0]) for row in cursor.fetchall()]

            if not single_paths:
                return

            for path in single_paths:
                try:
                    self.file_repo.set_status(
                        path,
                        FileStatus.KEEP,
                        reason="Single image default KEEP",
                        action_id="AUTO_KEEP_SINGLE",
                    )
                    self.stats.marked_keep += 1
                except Exception as e:
                    logger.error(f"Failed to mark single image as keep: {e}")
        except Exception as e:
            logger.error(f"Failed to process single images: {e}")
    
    def _store_duplicate_group(self, group_id: str, paths: list[Path]) -> None:
        """Store duplicate group in database."""
        cursor = self.db.conn.cursor()
        
        for path in paths:
            # Get file_id
            cursor.execute("SELECT file_id FROM files WHERE path = ?", (str(path),))
            row = cursor.fetchone()
            
            if row:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO duplicates (group_id, file_id, similarity_score)
                    VALUES (?, ?, ?)
                    """,
                    (group_id, row["file_id"], 1.0),
                )
        
        self.db.conn.commit()
    
    def _stage_cheap_filter(
        self, groups: dict[str, list[Path]]
    ) -> dict[str, list[Path]]:
        """
        Stage 3: Apply cheap filters to remove obvious bad images.
        
        Args:
            groups: Duplicate groups
            
        Returns:
            Filtered groups (with bad images removed)
        """
        filtered_groups = {}
        
        for group_id, paths in groups.items():
            # Analyze all images in group
            filter_results = self.cheap_filter.filter_batch(paths)
            
            # Keep only images that passed
            passed = [
                path for path, result in filter_results.items()
                if result.passed
            ]
            
            failed_count = len(paths) - len(passed)
            self.stats.passed_filter += len(passed)
            self.stats.failed_filter += failed_count
            
            if failed_count > 0:
                logger.info(
                    f"Group {group_id}: {failed_count} images filtered out, "
                    f"{len(passed)} remaining"
                )
            
            # Only keep group if at least 2 images remain
            if len(passed) > 1:
                filtered_groups[group_id] = passed
            elif len(passed) == 1:
                # Only one image left, mark as KEEP
                try:
                    self.file_repo.set_status(
                        passed[0],
                        FileStatus.KEEP,
                        reason="Last remaining after cheap filter",
                        action_id="CHEAP_FILTER",
                    )
                except Exception as e:
                    logger.error(f"Failed to mark single image as keep: {e}")
        
        return filtered_groups
    
    def _stage_quality_analysis(
        self, groups: dict[str, list[Path]]
    ) -> dict[str, list]:
        """
        Stage 4: Analyze quality with Face Mesh (expensive).
        
        Optimized with caching: Cache hits skip expensive MediaPipe analysis.
        Only runs on images within duplicate groups.
        
        Args:
            groups: Filtered duplicate groups
            
        Returns:
            Dict mapping group_id to list of QualityResults
        """
        analyzed_groups = {}
        total_images = sum(len(paths) for paths in groups.values())
        
        logger.info(f"Analyzing {total_images} images across {len(groups)} groups")
        
        for group_id, paths in groups.items():
            # Check cache for existing analyses
            if self.cache_manager and not self.config.force_reanalyze:
                uncached_paths, cached_entries = self.cache_manager.bulk_lookup(
                    paths,
                    force_reanalyze=self.config.force_reanalyze,
                )
                
                if cached_entries:
                    logger.info(
                        f"Group {group_id}: {len(cached_entries)} cache hits, "
                        f"{len(uncached_paths)} require analysis"
                    )
                    self.stats.cache_hits += len(cached_entries)
                    self.stats.cache_misses += len(uncached_paths)
                
                # Analyze only uncached files
                if uncached_paths:
                    new_results = self._run_quality_batch(uncached_paths)
                    self.stats.analyzed_files += len(new_results)
                    
                    # Store new results in cache
                    for result in new_results:
                        self._store_cache_result(result)
                    
                    # Reconstruct full results list: cached + newly analyzed
                    all_results = []
                    
                    # Add newly analyzed results
                    all_results.extend(new_results)
                    
                    # Add cached results (reconstruct from CacheEntry)
                    for file_path, cache_entry in cached_entries.items():
                        # Create a synthetic result object with cached data
                        cached_result = self._create_cached_result(file_path, cache_entry)
                        all_results.append(cached_result)
                    
                    analyzed_groups[group_id] = all_results
                else:
                    # All files were cached
                    cached_results = [
                        self._create_cached_result(file_path, cache_entry)
                        for file_path, cache_entry in cached_entries.items()
                    ]
                    analyzed_groups[group_id] = cached_results
            else:
                # Cache disabled or force_reanalyze enabled
                if self.config.force_reanalyze:
                    logger.info(f"Group {group_id}: force_reanalyze enabled, skipping cache")

                results = self._run_quality_batch(paths)
                self.stats.analyzed_files += len(results)
                
                # Store all results in cache if cache is enabled
                if self.cache_manager:
                    for result in results:
                        self._store_cache_result(result)
                
                analyzed_groups[group_id] = results
        
        return analyzed_groups

    def _run_quality_batch(self, paths: list[Path]) -> list:
        """Run quality analysis with optional process-parallel backend."""
        if self._use_process_parallel and self._parallel_quality_analyzer is not None and len(paths) > 1:
            return self._parallel_quality_analyzer.analyze_batch_parallel(
                paths,
                max_workers=self.config.max_workers,
                batch_size=1,
            )
        return self.quality_analyzer.analyze_batch(paths)
    
    def _stage_score_and_mark(
        self, groups: dict[str, list]
    ) -> dict[str, int]:
        """
        Stage 5: Score images and mark top N to keep.
        
        Also auto-selects best image per group for recommendation.
        
        Args:
            groups: Dict of quality results per group
            
        Returns:
            Statistics from scoring
        """
        # Score all groups
        group_scores = self.scorer.score_multiple_groups(groups)
        
        # Auto-select best image per group for recommendation
        logger.info("Auto-selecting best image per group...")
        for group_id, quality_results in groups.items():
            best_image_path, second_image_path, _ = self.scorer.auto_select_best_image(group_id, quality_results)
            
            try:
                cursor = self.db.conn.cursor()
                # Reset group recommendations
                cursor.execute(
                    """
                    UPDATE files
                    SET is_recommended = 0, keeper_source = 'undecided'
                    WHERE file_id IN (
                        SELECT file_id FROM duplicates WHERE group_id = ?
                    )
                    """,
                    (group_id,)
                )
                if best_image_path:
                    cursor.execute(
                        """
                        UPDATE files 
                        SET is_recommended = 1, keeper_source = 'auto'
                        WHERE path = ?
                        """,
                        (str(best_image_path),)
                    )
                if second_image_path:
                    cursor.execute(
                        """
                        UPDATE files 
                        SET keeper_source = 'auto_secondary'
                        WHERE path = ?
                        """,
                        (str(second_image_path),)
                    )
                self.db.conn.commit()
                if best_image_path:
                    logger.debug(f"Marked {best_image_path.name} as recommended")
                if second_image_path:
                    logger.debug(f"Marked {second_image_path.name} as auto_secondary")
            except Exception as e:
                logger.warning(f"Failed to mark recommendations for group {group_id}: {e}")
        
        # Apply to database
        action_id = f"PIPELINE_{uuid.uuid4().hex[:8]}"
        stats = self.scorer.apply_scores_to_db(
            group_scores,
            self.file_repo,
            action_id=action_id,
        )
        
        return stats
    
    def _log_stats(self) -> None:
        """Log final pipeline statistics."""
        logger.info("=" * 60)
        logger.info("PIPELINE STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Indexed:        {self.stats.indexed_files} files")
        logger.info(f"Duplicates:     {self.stats.duplicate_groups} groups, {self.stats.total_duplicates} files")
        logger.info(f"Cheap filter:   {self.stats.passed_filter} passed, {self.stats.failed_filter} filtered")
        logger.info(f"Analyzed:       {self.stats.analyzed_files} files")
        
        # Log cache statistics if enabled
        if self.cache_manager:
            logger.info(f"Cache hits:     {self.stats.cache_hits} files (from cache)")
            logger.info(f"Cache misses:   {self.stats.cache_misses} files (newly analyzed)")
            if self.stats.cache_hits + self.stats.cache_misses > 0:
                hit_rate = self.stats.cache_hits / (self.stats.cache_hits + self.stats.cache_misses) * 100
                logger.info(f"Cache hit rate: {hit_rate:.1f}%")
        
        logger.info(f"Marked KEEP:    {self.stats.marked_keep} files")
        logger.info(f"Marked DELETE:  {self.stats.marked_delete} files")
        logger.info(f"Skipped locked: {self.stats.skipped_locked} files")
        logger.info("=" * 60)
    
    def _store_cache_result(self, quality_result) -> None:
        """
        Store a quality analysis result in cache.
        
        Args:
            quality_result: Result from QualityAnalyzer.analyze_batch()
        """
        if not self.cache_manager:
            return
        
        try:
            file_path = quality_result.file_path
            quality_score = quality_result.quality_score
            
            # Determine if file is top-N (will be set by scorer later, so default False)
            top_n_flag = False
            
            # Collect metadata
            metadata = {
                "faces_detected": getattr(quality_result, "faces_detected", 0),
                "laplacian_variance": getattr(quality_result, "laplacian_variance", None),
                "brightness": getattr(quality_result, "brightness", None),
                "width": getattr(quality_result, "width", None),
                "height": getattr(quality_result, "height", None),
            }
            
            self.cache_manager.store(
                file_path=file_path,
                quality_score=quality_score,
                top_n_flag=top_n_flag,
                metadata=metadata,
            )
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")
    
    def _create_cached_result(self, file_path: Path, cache_entry):
        """
        Create a synthetic QualityResult object from cached data.
        
        This reconstructs a result object that matches the QualityAnalyzer output
        format, allowing seamless integration into the scoring stage.
        
        Args:
            file_path: Path to the image
            cache_entry: CacheEntry from cache manager
            
        Returns:
            Object compatible with GroupScorer.score_multiple_groups()
        """
        # Import here to avoid circular imports
        from photo_cleaner.pipeline.quality_analyzer import QualityResult
        
        try:
            metadata = cache_entry.metadata or {}
            
            # Create synthetic result object
            class CachedQualityResult:
                def __init__(self, path, score, metadata_dict):
                    self.file_path = path
                    self.quality_score = score
                    self.faces_detected = metadata_dict.get("faces_detected", 0)
                    self.laplacian_variance = metadata_dict.get("laplacian_variance", 0.0)
                    self.brightness = metadata_dict.get("brightness", 128)
                    self.width = metadata_dict.get("width", 0)
                    self.height = metadata_dict.get("height", 0)
                    self.from_cache = True
            
            result = CachedQualityResult(file_path, cache_entry.quality_score, metadata)
            logger.debug(f"Loaded {file_path.name} from cache (score={cache_entry.quality_score:.2f})")
            return result
        except Exception as e:
            logger.warning(f"Failed to create cached result for {file_path}: {e}")
            return None



def run_final_pipeline(
    folder_path: Path | str,
    db_path: Path | str,
    top_n: int = 3,
    hash_dist: int = 5,
    use_face_mesh: bool = True,
    use_cache: bool = True,
    force_reanalyze: bool = False,
) -> PipelineStats:
    """
    Run the complete PhotoCleaner pipeline.
    
    Args:
        folder_path: Path to folder with photos
        db_path: Path to SQLite database
        top_n: Number of top images to keep per group
        hash_dist: Hamming distance threshold for duplicates
        use_face_mesh: Enable MediaPipe Face Mesh analysis
        use_cache: Enable result caching (default True for performance)
        force_reanalyze: If True, ignore cache and re-analyze all images
        
    Returns:
        Pipeline statistics
    """
    folder_path = Path(folder_path)
    db_path = Path(db_path)
    
    # Initialize database
    db = Database(db_path)
    
    # Create pipeline config
    config = PipelineConfig(
        hash_distance_threshold=hash_dist,
        top_n=top_n,
        use_face_mesh=use_face_mesh,
        use_cache=use_cache,
        force_reanalyze=force_reanalyze,
    )
    
    # Run pipeline
    pipeline = PhotoCleanerPipeline(db, config)
    stats = pipeline.run(folder_path)
    
    return stats
