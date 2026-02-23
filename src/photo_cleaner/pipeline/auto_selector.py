"""
Auto-Selection of Best Image per Duplicate Group

Deterministic, rule-based selection (not ML/black-box).
Scores images by:
1. Eye Status (DOMINANT: 55%)
   - Eyes open with face present → Good
   - Eyes closed with face present → Strong penalty (5%)
   - No face detected → Neutral (60%)
2. Sharpness (20% weight): Laplacian variance
3. Lighting (15% weight): Exposure analysis
4. Resolution (10% weight): Megapixels
5. Recency (0% weight): EXIF timestamp (reserved for future group context)

In RELEASE mode, only final recommendations logged.
In DEBUG mode, full score breakdown for all images logged.

User can always override the recommendation.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from PIL import Image
    from PIL.Image import Exif
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Register HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

from photo_cleaner.config import AppConfig
from photo_cleaner.pipeline.scoring_constants import ScoringConstants  # BUG-M1 FIX

logger = logging.getLogger(__name__)


@dataclass
class ImageScoreComponents:
    """Detailed breakdown of an image's score."""
    
    path: Path
    
    # Individual component scores (0-100)
    sharpness_score: float = 0.0
    lighting_score: float = 0.0
    resolution_score: float = 0.0
    face_quality_score: float = 0.0
    recency_score: float = 0.0
    
    # Overall weighted score
    total_score: float = 0.0
    
    # Metadata
    reason: str = ""  # Why this was chosen
    disqualified: bool = False
    disqualify_reason: str = ""
    
    def __post_init__(self):
        """Calculate total score if not set."""
        # Note: total_score is now calculated in _score_image with the new weights
        # This __post_init__ is kept for backward compatibility but shouldn't be used
        pass


class AutoSelector:
    """Automatically select best image from a duplicate group."""
    
    def __init__(self):
        """Initialize auto selector."""
        self.pil_available = PIL_AVAILABLE
    
    def select_best_image(
        self,
        images: list[Path],
        quality_results: dict[Path, dict],  # path -> quality metrics
    ) -> tuple[Optional[Path], Optional[ImageScoreComponents]]:
        """
        Select best image from group.
        
        Args:
            images: List of image paths in group
            quality_results: Dict mapping path to quality metrics
                            {quality_score, sharpness_score, resolution, face_quality, etc}
        
        Returns:
            (best_image_path, score_components)
        """
        if not images:
            raise ValueError("No images provided")
        
        if len(images) == 1:
            single_score = self._score_image(images[0], quality_results.get(images[0], {}))
            if single_score.disqualified:
                # BUG-M2 FIX: Use warning level for important condition (no recommendation possible)
                logger.warning(f"Single image {images[0].name} disqualified (closed eyes/quality error) - no recommendation")
                return None, None
            return images[0], single_score
        
        # PHASE 3 TASK 2: Calculate group-median resolution for adaptive baseline
        group_resolutions = []
        for img_path in images:
            quality_data = quality_results.get(img_path, {})
            if "resolution" in quality_data:
                res = quality_data["resolution"]
                if isinstance(res, (list, tuple)) and len(res) >= 2:
                    # BUG-H1 FIX: Validate resolution values are positive and realistic
                    if res[0] > 0 and res[1] > 0:  # Width and height must be positive
                        mp = (res[0] * res[1]) / 1_000_000
                        if mp > 0.1:  # At least 0.1MP to filter out garbage data (e.g., 1x1 pixel)
                            group_resolutions.append(mp)
                        else:
                            logger.debug(f"Skipping unrealistic resolution {res} ({mp:.3f}MP) for {img_path.name}")
                    else:
                        logger.debug(f"Skipping invalid resolution {res} (zero or negative) for {img_path.name}")
        
        # Calculate median resolution for this group (None if insufficient data)
        group_median_resolution = None
        if group_resolutions:
            group_resolutions.sort()
            mid = len(group_resolutions) // 2
            if len(group_resolutions) % 2 == 0:
                group_median_resolution = (group_resolutions[mid-1] + group_resolutions[mid]) / 2
            else:
                group_median_resolution = group_resolutions[mid]
            logger.debug(f"[PHASE-3] Group median resolution: {group_median_resolution:.1f}MP")
        
        # Score each image
        scored_images = []
        for img_path in images:
            score_comp = self._score_image(
                img_path, 
                quality_results.get(img_path, {}),
                group_median_resolution=group_median_resolution  # PHASE 3: Pass to scorer
            )
            scored_images.append(score_comp)

        usable = [s for s in scored_images if not s.disqualified]
        if not usable:
            logger.warning("Alle Bilder disqualifiziert (geschlossene Augen/Qualitätsfehler) – keine Empfehlung")
            return None, None

        # Highest total_score among usable
        best_img = max(usable, key=lambda x: x.total_score)
        
        # Log all candidates (always, but with appropriate detail level)
        usable_sorted = sorted(usable, key=lambda x: x.total_score, reverse=True)
        
        if AppConfig.is_debug():
            # DEBUG: Log detailed scoring for top 3 candidates
            logger.info(f"⭐ Auto-Auswahl für Gruppe (Augen-Gewicht: 55%):")
            for i, candidate in enumerate(usable_sorted[:3], 1):
                marker = "⭐ EMPFOHLEN" if i == 1 else f"#{i}"
                logger.info(
                    f"  {marker}: {candidate.path.name} → Score {candidate.total_score:.2f} "
                    f"({candidate.reason})"
                )
        else:
            # RELEASE: Log only the selected image
            best = usable_sorted[0]
            logger.info(f"⭐ Empfohlen: {best.path.name} (Score: {best.total_score:.1f})")
        
        return best_img.path, best_img
    
    def _score_image(
        self,
        image_path: Path,
        quality_data: dict,
        group_median_resolution: Optional[float] = None,  # PHASE 3 TASK 2: Group median
    ) -> ImageScoreComponents:
        """
        Score a single image based on multiple criteria.
        
        Args:
            image_path: Path to image
            quality_data: Quality analysis dict with keys like:
                - sharpness_score (0-100)
                - overall_score (0-100)
                - resolution (width, height tuple or megapixels float)
                - face_quality: FaceQuality object or dict
                - lighting_score (0-100)
        
        Returns:
            ImageScoreComponents with detailed breakdown
        """
        components = ImageScoreComponents(path=image_path)
        disqualify_flags = []
        
        # 1. SHARPNESS (0-100)
        sharpness = quality_data.get("sharpness_score", 50.0)
        resolution = quality_data.get("resolution", (800, 600))
        if isinstance(sharpness, (int, float)):
            # Normalize Laplacian variance to 0-100
            # Typical range: 0-500 (blurry to sharp)
            # PHASE 2 FIX [BUG-M4]: Resolution-aware sharpness normalization
            # Higher resolution images have naturally higher Laplacian variance (noise + detail)
            # Lower resolution images need scaled down for fair comparison
            # PHASE 3 TASK 3: Camera-aware sharpness normalization
            # Different phones have different processing characteristics
            
            # Calculate megapixels for scaling
            if isinstance(resolution, (list, tuple)) and len(resolution) >= 2:
                mp = (resolution[0] * resolution[1]) / 1_000_000
            else:
                mp = float(resolution) if isinstance(resolution, (int, float)) else ScoringConstants.SHARPNESS_REFERENCE_RESOLUTION_MP
            
            # Adaptive normalization: base divisor for reference resolution, scale with actual resolution
            # Higher MP → higher expected sharpness variance → higher divisor
            # This prevents high-res images from always scoring higher on sharpness
            resolution_factor = mp / ScoringConstants.SHARPNESS_REFERENCE_RESOLUTION_MP
            
            # PHASE 3: Add camera-aware factor (from CameraProfile calibration)
            # Different cameras have different processing, affecting sharpness variance
            from photo_cleaner.pipeline.quality_analyzer import CameraProfile
            camera_model = quality_data.get("camera_model", "unknown")
            camera_factor = CameraProfile.get_sharpness_factor(camera_model)
            
            sharp_divisor = ScoringConstants.SHARPNESS_BASE_DIVISOR * resolution_factor * camera_factor
            # NOTE: Basis: Typical Laplacian variance for 8MP photos is 0-500
            # Resolution-aware ranges:
            #  - 5MP: 0-350 variance (lower detail density)
            #  - 8MP: 0-500 variance (baseline)
            #  - 12MP: 0-650 variance (higher detail density)
            #  - 48MP: 0-1200 variance (very high detail)
            
            # PHASE 4 FIX 2: ISO-aware sharpness scoring for low-light photos
            # High ISO (1600+) causes natural grain/noise that reduces sharpness score
            # Relax sharpness threshold for high-ISO photos to avoid unfair penalty
            exif_data = quality_data.get("exif_data", {})
            iso_value = exif_data.get("iso_value") if exif_data else None
            
            # BUG-C1 FIX: Initialize iso_tolerance_factor BEFORE conditional to prevent division by zero
            iso_tolerance_factor = 1.0
            if iso_value and iso_value > 0:  # Validate iso_value is positive
                if iso_value >= ScoringConstants.ISO_THRESHOLD_VERY_HIGH:
                    iso_tolerance_factor = ScoringConstants.ISO_TOLERANCE_VERY_HIGH
                elif iso_value >= ScoringConstants.ISO_THRESHOLD_HIGH:
                    iso_tolerance_factor = ScoringConstants.ISO_TOLERANCE_HIGH
                elif iso_value >= ScoringConstants.ISO_THRESHOLD_MEDIUM:
                    iso_tolerance_factor = ScoringConstants.ISO_TOLERANCE_MEDIUM
            
            # Apply ISO adjustment to divisor (higher divisor = more lenient scoring)
            # BUG-C1 FIX: Safety check to prevent division by zero
            if iso_tolerance_factor <= 0:
                iso_tolerance_factor = 1.0
            sharp_divisor = sharp_divisor / iso_tolerance_factor
            
            # BUG-C3 FIX: Use absolute value to handle negative Laplacian variance (rare but possible)
            # Negative variance can occur with extremely dark images or bitmap artifacts
            sharpness_abs = abs(sharpness)
            components.sharpness_score = min(100, max(0, sharpness_abs / sharp_divisor))
            
            if AppConfig.is_debug() and iso_value and iso_value >= 800:
                logger.debug(
                    f"[PHASE-4] ISO-aware sharpness: {image_path.name} ISO={iso_value} "
                    f"tolerance={iso_tolerance_factor:.2f} adjusted_divisor={sharp_divisor:.1f}"
                )
        
        # 2. LIGHTING (0-100)
        # Extract from overall_score or compute from brightness
        overall_score = quality_data.get("overall_score", 50.0)
        lighting = quality_data.get("lighting_score", overall_score)
        components.lighting_score = min(100, max(0, float(lighting)))
        
        # 3. RESOLUTION (0-100)
        # Higher res = higher score
        resolution = quality_data.get("resolution", (800, 600))
        if isinstance(resolution, (list, tuple)) and len(resolution) >= 2:
            megapixels = (resolution[0] * resolution[1]) / 1_000_000
        else:
            megapixels = float(resolution) if isinstance(resolution, (int, float)) else 8.0
        
        # PHASE 2 FIX [BUG-M3]: Adaptive resolution scaling
        # Previously: 8MP = 100%, 2MP = 25%, all modern phones (12-108MP) at 100%
        # Now: Normalize to camera's ERA to prevent uniformity in high-res groups
        # Strategy: Use adaptive baseline where median image sets the 100% mark
        # PHASE 3 TASK 2: Use group-median resolution if available (most fair)
        # Fallback to era-aware baseline (12MP for modern, 8MP for legacy)
        # This prevents 48MP photos from always scoring 100% in mixed-generation groups
        
        if group_median_resolution is not None:
            # PHASE 3: Use group median as baseline for fairness
            adaptive_baseline = group_median_resolution
            logger.debug(f"[PHASE-3] Using group-median baseline {adaptive_baseline:.1f}MP for {image_path.name}")
        else:
            # PHASE 2: Fallback to era-aware baseline
            adaptive_baseline = ScoringConstants.RESOLUTION_BASELINE_MODERN  # Modern smartphone standard (2020+)
            # Fallback to legacy baseline for groups with clearly older cameras
            if megapixels < ScoringConstants.RESOLUTION_BASELINE_LEGACY:
                adaptive_baseline = ScoringConstants.RESOLUTION_BASELINE_LEGACY
        
        res_score = (megapixels / adaptive_baseline) * 100
        components.resolution_score = min(100, max(0, res_score))
        
        # DEBUG: Log resolution details
        if AppConfig.is_debug():
            orientation = "Portrait" if (isinstance(resolution, (list, tuple)) and resolution[1] > resolution[0]) else "Landscape"
            logger.debug(
                f"AutoSelector: {image_path.name} → {orientation} {resolution} = {megapixels:.1f}MP → score={res_score:.0f}%"
            )
        
        # Extract face quality data (single point)
        face_quality = quality_data.get("face_quality", None)
        has_face = False
        all_eyes_open = False
        confidence = 0.0
        num_faces = 0
        person_statuses = []
        
        if face_quality:
            # BUG-C4 FIX: Check for error dictionary first to prevent AttributeError
            # Face detection can return error dict like {"error": "MediaPipe timeout"}
            if isinstance(face_quality, dict):
                if "error" in face_quality:
                    # Error case: treat as no face detected (neutral scoring)
                    logger.debug(f"Face detection error for {image_path.name}: {face_quality.get('error')}")
                    has_face = False
                else:
                    # Normal dict case
                    has_face = face_quality.get("has_face", False)
                    all_eyes_open = face_quality.get("all_eyes_open", False)
                    confidence = face_quality.get("confidence", 0.0)
                    num_faces = face_quality.get("num_faces", 0)
                    person_statuses = face_quality.get("person_eye_statuses", [])
            else:
                # FaceQuality object - strict type checking (no legacy fallbacks)
                # RATIONALE [BUG-M2]: Legacy fallback to 'eyes_open' was problematic.
                # With multiprocessing & caching, old FaceQuality objects can persist → undefined behavior.
                # FIX: Require explicit 'all_eyes_open' field. If missing, use 'has_face' only.
                has_face = getattr(face_quality, "has_face", False)
                all_eyes_open = getattr(face_quality, "all_eyes_open", False)
                # NO FALLBACK: If 'all_eyes_open' not present, use False (safer)
                confidence = getattr(face_quality, "confidence", 0.0)
                num_faces = getattr(face_quality, "num_faces", 0)
                person_statuses = getattr(face_quality, "person_eye_statuses", [])
        
        # 4. FACE QUALITY SCORING (0-100)
        if has_face:
            if all_eyes_open:
                # Good: face(s) with ALL eyes open
                components.face_quality_score = min(
                    100, 
                    ScoringConstants.FACE_QUALITY_BASE_SCORE + confidence * ScoringConstants.FACE_QUALITY_CONFIDENCE_BOOST
                )
                if AppConfig.is_debug():
                    logger.debug(
                        f"{image_path.name}: {num_faces} face(s) with OPEN eyes ✅ → Score {components.face_quality_score:.1f}"
                    )
            else:
                # Some faces detected but NOT all eyes open → apply malus (see BUG-M1)
                components.face_quality_score = ScoringConstants.FACE_QUALITY_CLOSED_EYES_MALUS
                if AppConfig.is_debug():
                    # BUG-M2 FIX: Use info level for important decision (malus applied)
                    logger.info(
                        f"{image_path.name}: ⚠️  At least one person with closed eyes → Face-Score {ScoringConstants.FACE_QUALITY_CLOSED_EYES_MALUS:.0f}% (malus)"
                    )
                    if person_statuses:
                        for person_status in person_statuses:
                            status_str = "✅ OPEN" if person_status.eyes_open else "❌ CLOSED"
                            logger.debug(f"  Person {person_status.person_id}: Eyes {status_str}")
        else:
            # No faces detected = neutral (not penalized, not rewarded)
            # NOTE [BUG-C4]: This is different from face detection ERROR (which would be caught earlier)
            # Error case: face_quality is None or has error_message → should NOT reach here
            components.face_quality_score = ScoringConstants.FACE_QUALITY_NO_FACE_NEUTRAL
        
        # 5. RECENCY (0-100)
        # BUG-L2 FIX: Recency has 0% weight (WEIGHT_RECENCY = 0.00)
        # EXIF datetime parsing is currently dead code - reserved for future group-context scoring
        # TODO: Re-enable when implementing temporal scoring within duplicate groups
        # For now: hardcoded neutral value, no parsing overhead
        components.recency_score = 50.0  # Neutral; reserved for future
        
        # POLICY [BUG-M1]: If faces detected and NOT all_eyes_open → Apply MALUS (not disqualification)
        # RATIONALE: Hard-rule disqualification (5%) was too aggressive for duplicate groups with mixed content.
        # Example: Group with 5 photos (4 eyes-open, 1 blink) → top-N should consider all 5, not just 4.
        # Instead: Apply malus to face_quality_score to penalize but not eliminate.
        # Score reduction: from 70% (normal face) → 20% (closed eyes) = strong penalty but still competitive
        if has_face and not all_eyes_open:
            # Malus is already applied above in face_quality_score = 20
            # Don't add to disqualify_flags - this is NOT a disqualification anymore
            if AppConfig.is_debug() and person_statuses:
                for person_status in person_statuses:
                    if not person_status.eyes_open:
                        logger.info(
                            f"⚠️  {image_path.name}: "
                            f"Person {person_status.person_id} has CLOSED eyes → Face-Score {ScoringConstants.FACE_QUALITY_CLOSED_EYES_MALUS:.0f}% (malus, not disqualified)"
                        )

        # Set reason
        components.reason = (
            f"Sharp:{components.sharpness_score:.0f}% "
            f"Light:{components.lighting_score:.0f}% "
            f"Res:{components.resolution_score:.0f}% "
            f"Face:{components.face_quality_score:.0f}%"
        )
        
        # Recalculate weighted score using constants (BUG-M1 FIX)
        weights = ScoringConstants.get_weights()  # [0.20, 0.15, 0.10, 0.55, 0.00]
        scores = [
            components.sharpness_score,
            components.lighting_score,
            components.resolution_score,
            components.face_quality_score,
            components.recency_score,
        ]
        components.total_score = sum(w * s for w, s in zip(weights, scores))
        
        # DEBUG: Log detailed scoring breakdown
        if AppConfig.is_debug():
            logger.debug(
                f"Score {image_path.name}: Sharp={components.sharpness_score:.1f} "
                f"Light={components.lighting_score:.1f} Res={components.resolution_score:.1f} "
                f"Face={components.face_quality_score:.1f} → TOTAL={components.total_score:.2f}"
            )

        # Handle any remaining disqualify flags (currently none from eye-logic due to BUG-M1 fix)
        if disqualify_flags:
            components.disqualified = True
            components.disqualify_reason = ", ".join(disqualify_flags)
            components.reason += f" | Ausschluss: {components.disqualify_reason}"
            # NOTE [BUG-L2]: Only log disqualification in DEBUG mode to avoid verbose logging
            if AppConfig.is_debug():
                logger.warning(
                    f"🚫 DISQUALIFIZIERT: {image_path.name} → {components.disqualify_reason} "
                    f"(Raw-Score: {components.total_score:.2f})"
                )
        
        return components
    
    def _get_exif_datetime(self, image_path: Path) -> Optional[datetime]:
        """
        Extract EXIF datetime from image.
        
        Priority:
        1. EXIF DateTimeOriginal
        2. EXIF CreateDate
        3. File mtime
        
        Args:
            image_path: Path to image file
        
        Returns:
            datetime object or None
        """
        if not self.pil_available:
            return None
        
        try:
            with Image.open(image_path) as img:
                exif = img.getexif()
                
                # Try DateTimeOriginal (tag 36867)
                if 36867 in exif:
                    dt_str = exif[36867]
                    return self._parse_exif_datetime(dt_str)
                
                # Try CreateDate (tag 36868)
                if 36868 in exif:
                    dt_str = exif[36868]
                    return self._parse_exif_datetime(dt_str)
        except Exception as e:
            logger.debug(f"Failed to read EXIF from {image_path}: {e}")
        
        # Fallback: file mtime
        try:
            mtime = image_path.stat().st_mtime
            return datetime.fromtimestamp(mtime)
        except (OSError, ValueError):
            logger.debug(f"Could not read modification time: {image_path}", exc_info=True)
            return None
    
    @staticmethod
    def _parse_exif_datetime(dt_str: str) -> Optional[datetime]:
        """Parse EXIF datetime string (format: 'YYYY:MM:DD HH:MM:SS')."""
        try:
            return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        except (ValueError, TypeError):
            return None


def auto_select_best_image(
    images: list[Path],
    quality_results: dict[Path, dict],
) -> tuple[Optional[Path], Optional[ImageScoreComponents]]:
    """
    Convenience function: Select best image from group.
    
    Args:
        images: List of image paths
        quality_results: Quality metrics per image
    
    Returns:
        (best_image_path, score_breakdown)
    """
    selector = AutoSelector()
    return selector.select_best_image(images, quality_results)
