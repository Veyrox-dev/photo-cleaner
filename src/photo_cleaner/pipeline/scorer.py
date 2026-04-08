"""
Group Scorer

Scores and ranks images within duplicate groups.
Marks top N images to keep, rest to delete.
Auto-selects best image per group for recommendation.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from photo_cleaner.pipeline.quality_analyzer import QualityResult
from photo_cleaner.pipeline.auto_selector import AutoSelector, ImageScoreComponents
from photo_cleaner.models.status import FileStatus

logger = logging.getLogger(__name__)


@dataclass
class ScoredImage:
    """Image with final score and ranking."""
    
    path: Path
    total_score: float
    rank: int
    should_keep: bool
    quality_result: Optional[QualityResult] = None


@dataclass
class GroupScore:
    """Scoring result for a duplicate group."""
    
    group_id: str
    images: list[ScoredImage]
    top_n: int
    num_keep: int
    num_delete: int


class GroupScorer:
    """
    Scores images within duplicate groups and marks top N to keep.
    """
    
    def __init__(self, top_n: int = 3):
        """
        Initialize group scorer.
        
        Args:
            top_n: Number of top images to keep per group
        """
        self.top_n = top_n
        self.auto_selector = AutoSelector()

    def _effective_top_n_for_group(self, group_size: int) -> int:
        """Return dynamic keep count based on group size.

        Policy:
        - <6 images: keep 1
        - 6-11 images: keep 2
        - >=12 images: keep 3

        The configured `top_n` acts as an upper cap.
        """
        if group_size >= 12:
            dynamic_top_n = 3
        elif group_size >= 6:
            dynamic_top_n = 2
        else:
            dynamic_top_n = 1
        return max(1, min(self.top_n, dynamic_top_n))
    
    def score_group(
        self,
        group_id: str,
        quality_results: list[QualityResult],
    ) -> GroupScore:
        """Score images and mark Top N as KEEP, rest as DELETE (sorted by score)."""
        valid_results = [r for r in quality_results if r.error is None]
        
        if not valid_results:
            logger.warning(f"Gruppe {group_id}: Keine gültigen Quality-Ergebnisse")
            return GroupScore(
                group_id=group_id,
                images=[],
                top_n=self.top_n,
                num_keep=0,
                num_delete=0,
            )
        
        # Get full score list from auto_selector
        _, _, all_scores = self.auto_select_best_image(group_id, valid_results)
        effective_top_n = self._effective_top_n_for_group(len(valid_results))
        
        # Create scored images: Top N = KEEP, rest = DELETE (ignore disqualified status here)
        scored_images = []
        usable_count = 0
        for rank, item in enumerate(all_scores, start=1):
            # Handle both old format (3-tuple) and new format (4-tuple with components)
            if len(item) == 4:
                path, total_score, disqualified, components = item
            else:
                path, total_score, disqualified = item
            
            # Only count non-disqualified for keep/delete
            if not disqualified:
                usable_count += 1
                should_keep = usable_count <= effective_top_n
            else:
                should_keep = False
            
            # Find matching QualityResult
            qr = next((r for r in valid_results if r.path == path), None)
            
            scored_images.append(
                ScoredImage(
                    path=path,
                    total_score=total_score,
                    rank=rank,
                    should_keep=should_keep,
                    quality_result=qr,
                )
            )
        
        num_keep = sum(1 for img in scored_images if img.should_keep)
        num_delete = len(scored_images) - num_keep
        
        logger.info(
            f"🎯 Gruppe {group_id}: {len(scored_images)} Bilder bewertet → "
            f"{num_keep} KEEP, {num_delete} DELETE"
        )
        
        return GroupScore(
            group_id=group_id,
            images=scored_images,
            top_n=effective_top_n,
            num_keep=num_keep,
            num_delete=num_delete,
        )
    
    def score_multiple_groups(
        self,
        groups: dict[str, list[QualityResult]],
    ) -> list[GroupScore]:
        """
        Score multiple duplicate groups.
        
        PHASE 3 TASK 5: Multi-group normalization for fair cross-group comparison
        Analyzes all groups to compute global normalization baselines.
        
        Args:
            groups: Dict mapping group_id to list of quality results
            
        Returns:
            List of GroupScores
        """
        logger.info("=== GroupScorer.score_multiple_groups() STARTED ===")
        logger.info(f"Scoring {len(groups)} groups...")
        # PHASE 3 TASK 5: Pre-compute global baselines for cross-group fairness
        global_resolution_baseline = self._compute_global_resolution_baseline(groups)
        global_sharpness_baseline = self._compute_global_sharpness_baseline(groups)
        
        if global_resolution_baseline:
            logger.info(f"[PHASE-3] Global resolution baseline: {global_resolution_baseline:.1f}MP")
        if global_sharpness_baseline:
            logger.info(f"[PHASE-3] Global sharpness baseline: {global_sharpness_baseline:.1f}")
        
        group_scores = []
        
        for group_id, quality_results in groups.items():
            score = self.score_group(group_id, quality_results)
            group_scores.append(score)
        
        logger.info(f"=== GroupScorer.score_multiple_groups() COMPLETED ===")
        logger.info(f"Scored {len(group_scores)} groups")
        return group_scores
    
    def _compute_global_resolution_baseline(
        self,
        groups: dict[str, list[QualityResult]],
    ) -> Optional[float]:
        """PHASE 3 TASK 5: Compute median resolution across ALL groups.
        
        This provides a global baseline for fair cross-group comparison.
        Prevents one group's high-res photos from overwhelming another group's medium-res.
        
        Returns:
            Median resolution in megapixels, or None if no data available
        """
        all_resolutions = []
        
        for group_id, results in groups.items():
            for qr in results:
                if qr.error is None and qr.width > 0 and qr.height > 0:
                    mp = (qr.width * qr.height) / 1_000_000
                    all_resolutions.append(mp)
        
        if not all_resolutions:
            return None
        
        all_resolutions.sort()
        mid = len(all_resolutions) // 2
        if len(all_resolutions) % 2 == 0:
            return (all_resolutions[mid-1] + all_resolutions[mid]) / 2
        return all_resolutions[mid]
    
    def _compute_global_sharpness_baseline(
        self,
        groups: dict[str, list[QualityResult]],
    ) -> Optional[float]:
        """PHASE 3 TASK 5: Compute median sharpness across ALL groups.
        
        Different groups might have systematically different sharpness (e.g., phone
        vs film scans). This baseline accounts for that variation.
        
        Returns:
            Median sharpness score, or None if no data available
        """
        all_sharpness = []
        
        for group_id, results in groups.items():
            for qr in results:
                if qr.error is None and qr.overall_sharpness > 0:
                    all_sharpness.append(qr.overall_sharpness)
        
        if not all_sharpness:
            return None
        
        all_sharpness.sort()
        mid = len(all_sharpness) // 2
        if len(all_sharpness) % 2 == 0:
            return (all_sharpness[mid-1] + all_sharpness[mid]) / 2
        return all_sharpness[mid]
    
    def apply_scores_to_db(
        self,
        group_scores: list[GroupScore],
        file_repository,
        action_id: str = "PIPELINE_SCORING",
    ) -> dict[str, int]:
        """
        Apply scoring decisions to database.
        
        Marks top N images as KEEP, rest as DELETE (but doesn't delete yet).
        Respects locked files.
        
        Args:
            group_scores: List of scored groups
            file_repository: FileRepository instance
            action_id: Action ID for history tracking
            
        Returns:
            Statistics dict with counts
        """
        logger.info("=== GroupScorer.apply_scores_to_db() STARTED ===")
        logger.info(f"Applying scores for {len(group_scores)} groups to database...")
        stats = {
            "marked_keep": 0,
            "marked_delete": 0,
            "skipped_locked": 0,
            "failed": 0,
        }
        
        for group in group_scores:
            for image in group.images:
                try:
                    # Check if file is locked
                    current_status, is_locked = file_repository.get_status(image.path)
                    
                    if is_locked:
                        logger.info(f"Skipping locked file: {image.path}")
                        stats["skipped_locked"] += 1
                        continue
                    
                    # Set status based on scoring
                    new_status = FileStatus.KEEP if image.should_keep else FileStatus.DELETE
                    
                    reason = (
                        f"Top {image.rank} in group (score: {image.total_score:.1f})"
                        if image.should_keep
                        else f"Rank {image.rank} in group (score: {image.total_score:.1f})"
                    )
                    
                    file_repository.set_status(
                        image.path,
                        new_status,
                        reason=reason,
                        action_id=action_id,
                    )
                    
                    if image.should_keep:
                        stats["marked_keep"] += 1
                    else:
                        stats["marked_delete"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to update status for {image.path}: {e}")
                    stats["failed"] += 1
        
        logger.info("=== GroupScorer.apply_scores_to_db() COMPLETED ===")
        logger.info(
            f"Applied scores: {stats['marked_keep']} keep, "
            f"{stats['marked_delete']} delete, {stats['skipped_locked']} skipped, "
            f"{stats['failed']} failed"
        )
        
        return stats
    
    def rank_all_images_absolute(
        self,
        groups: dict[str, list[QualityResult]],
        top_n: int = 100,
    ) -> list[tuple[Path, float, str]]:
        """PHASE 4 TASK 3: Rank all images absolutely across all duplicate groups.
        
        Provides an absolute ranking of the best photos in the entire library,
        independent of group membership. Useful for features like "Show best 100 photos".
        
        Uses global baselines computed during multi-group scoring to ensure fair
        cross-group comparison.
        
        Args:
            groups: Dict mapping group_id to list of quality results
            top_n: Maximum number of top images to return (default 100)
            
        Returns:
            List of (path, absolute_score, group_id) tuples sorted by score
        """
        # Compute global baselines for fair scoring
        global_resolution_baseline = self._compute_global_resolution_baseline(groups)
        global_sharpness_baseline = self._compute_global_sharpness_baseline(groups)
        
        logger.info(f"[PHASE-4] Absolute ranking across {len(groups)} groups")
        if global_resolution_baseline:
            logger.info(f"[PHASE-4] Global resolution baseline: {global_resolution_baseline:.1f}MP")
        if global_sharpness_baseline:
            logger.info(f"[PHASE-4] Global sharpness baseline: {global_sharpness_baseline:.1f}")
        
        # Collect all images with scores
        all_scored_images = []
        
        for group_id, quality_results in groups.items():
            valid_results = [r for r in quality_results if r.error is None]
            if not valid_results:
                continue
            
            # Build quality_data for auto_selector
            quality_data = {}
            for qr in valid_results:
                resolution = (qr.width, qr.height) if qr.width > 0 else (800, 600)
                quality_data[qr.path] = {
                    "sharpness_score": qr.overall_sharpness,
                    "overall_score": qr.total_score,
                    "lighting_score": qr.lighting_score,
                    "resolution": resolution,
                    "face_quality": qr.face_quality,
                    "camera_model": qr.camera_model,
                    "exif_data": qr.exif_data,
                }
            
            # Score all images in group
            for path in quality_data:
                comp = self.auto_selector._score_image(path, quality_data[path])
                if not comp.disqualified:  # Only include non-disqualified images
                    all_scored_images.append((path, comp.total_score, group_id))
        
        # Sort by score (descending) and take top N
        all_scored_images.sort(key=lambda x: x[1], reverse=True)
        top_images = all_scored_images[:top_n]
        
        logger.info(
            f"[PHASE-4] Absolute ranking: Found {len(all_scored_images)} usable images, "
            f"returning top {min(len(top_images), top_n)}"
        )
        
        # Log top 10
        if top_images:
            logger.info("[PHASE-4] 🏆 Top 10 images across entire library:")
            for rank, (path, score, group_id) in enumerate(top_images[:10], 1):
                logger.info(f"  #{rank}: {path.name:30s} Score={score:6.2f} (Group: {group_id})")
        
        return top_images
    
    def get_top_images(self, group_score: GroupScore) -> list[Path]:
        """Get paths of top N images in a group."""
        return [img.path for img in group_score.images if img.should_keep]
    
    def get_delete_candidates(self, group_score: GroupScore) -> list[Path]:
        """Get paths of images marked for deletion in a group."""
        return [img.path for img in group_score.images if not img.should_keep]
    
    def auto_select_best_image(
        self,
        group_id: str,
        quality_results: list[QualityResult],
    ) -> tuple[Optional[Path], Optional[Path], list[tuple[Path, float, bool]]]:
        """Auto-select best (and second-best) with full score list.

        Returns (best_path, second_path, all_scores_with_components) where:
        - all_scores_with_components: [(path, score, disqualified, components), ...] sorted by score
        - components: ImageScoreComponents with sharpness_score, lighting_score, etc.
        """
        if not quality_results:
            return None, None, []

        valid_results = [r for r in quality_results if r.error is None]
        if not valid_results:
            return None, None, []

        # Build quality_data
        quality_data = {}
        for qr in valid_results:
            resolution = (qr.width, qr.height) if qr.width > 0 else (800, 600)
            quality_data[qr.path] = {
                "sharpness_score": qr.overall_sharpness,
                "overall_score": qr.total_score,
                "lighting_score": qr.lighting_score,  # Jetzt echter Wert!
                "resolution": resolution,
                "face_quality": qr.face_quality,
                "camera_model": qr.camera_model,  # PHASE 3: Add camera detection
                "exif_data": qr.exif_data,  # PHASE 3: Add raw EXIF for future use
            }

        # Score all images
        scored = []
        for path in quality_data:
            comp = self.auto_selector._score_image(path, quality_data[path])
            scored.append(comp)

        # Sort by score (descending), track disqualified separately
        scored_sorted = sorted(scored, key=lambda c: c.total_score, reverse=True)
        usable = [c for c in scored_sorted if not c.disqualified]
        
        # Build full score list for all images (now includes components)
        all_scores = [(c.path, c.total_score, c.disqualified, c) for c in scored_sorted]
        
        logger.info(f"\n📈 Gruppe {group_id}: Score-Liste (Augen-Gewicht 55%):")
        for i, (path, score, disq, _) in enumerate(all_scores, 1):
            status = "❌ DISQUALIFIZIERT" if disq else "✅ Verwendbar"
            logger.info(f"  #{i}: {path.name:20s} Score={score:6.2f} {status}")
        
        if not usable:
            logger.warning(f"⚠️ Gruppe {group_id}: Alle Bilder disqualifiziert (Augen geschlossen)")
            return None, None, all_scores

        best = usable[0]
        second = usable[1] if len(usable) > 1 else None

        logger.info(
            f"\n⭐ Gruppe {group_id}: EMPFEHLUNG → {best.path.name} (Score: {best.total_score:.2f})"
        )
        if second:
            logger.info(
                f"🥈 Gruppe {group_id}: ZWEITBESTE → {second.path.name} (Score: {second.total_score:.2f})"
            )

        return best.path, second.path if second else None, all_scores


