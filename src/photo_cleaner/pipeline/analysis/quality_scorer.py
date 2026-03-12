"""
Quality Scoring Engine for Image Analysis

Extracts all quality scoring and face metrics calculations from QualityAnalyzer.
This module provides a dedicated QualityScorer class handling:

1. Technical Quality Metrics:
   - FFT-based global sharpness (0-100)
   - Local sharpness consistency (0-100)
   - Detail/texture score (0-100)
   - Foreground/background separation (0-100)
   - Lighting quality with exposure balance (0-100)
   - Color cast penalty (0-20)

2. Face-Specific Scoring:
   - Eye openness via Eye Aspect Ratio (EAR)
   - Gaze direction (forward/away detection)
   - Head pose (tilt/yaw analysis)
   - Smile detection (mouth aspect ratio)
   - Per-face sharpness calculation
   - Best person selection from multi-face images

3. Final Score Calculation:
   - Portrait Mode: 60% face quality + 40% technical
   - Landscape Mode: 100% technical quality
   - Motion blur/autofocus penalty detection

Dependencies:
- numpy (lazy-imported, provided by QualityAnalyzer)
- cv2 (lazy-imported, provided by QualityAnalyzer)
- ScoringConstants (from scoring_constants.py)
- FaceQuality, PersonEyeStatus (from models.py)
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from photo_cleaner.pipeline.analysis import FaceQuality, PersonEyeStatus
from photo_cleaner.pipeline.scoring_constants import ScoringConstants
from photo_cleaner.config import AppConfig

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
else:
    NDArray = object

logger = logging.getLogger(__name__)


class QualityScorer:
    """
    Dedicated quality scoring engine for image analysis.
    
    Handles all scoring calculations: technical metrics (sharpness, lighting,
    detail) and face-specific metrics (eyes, gaze, head pose, smile).
    
    Supports binary modes:
    - Portrait: Images with faces use face quality (60%) + technical (40%)
    - Landscape: Images without faces use pure technical scores (100%)
    
    Dependencies are injected to support lazy-loading pattern:
    - numpy: For array operations
    - cv2: For image processing (Laplacian, Sobel, histogram, etc.)
    """
    
    def __init__(self, np_module=None, cv2_module=None):
        """
        Initialize QualityScorer with optional numpy and cv2 references.
        
        Args:
            np_module: numpy module (if None, imported locally when needed)
            cv2_module: cv2 (OpenCV) module (if None, imported locally when needed)
        """
        self._np = np_module
        self._cv2 = cv2_module
    
    @property
    def np(self):
        """Lazy-load numpy if not provided."""
        if self._np is None:
            try:
                import numpy
                self._np = numpy
            except ImportError:
                logger.warning("NumPy not available in QualityScorer")
        return self._np
    
    @property
    def cv2(self):
        """Lazy-load cv2 if not provided."""
        if self._cv2 is None:
            try:
                import cv2
                self._cv2 = cv2
            except ImportError:
                logger.warning("OpenCV not available in QualityScorer")
        return self._cv2
    
    def calculate_base_score(
        self,
        overall_sharpness: float,
        local_sharpness: float,
        detail_score: float,
        fg_bg_score: float,
        lighting_score: float,
        resolution_score: float,
        face_quality: FaceQuality,
        width: int,
        height: int
    ) -> float:
        """
        Phase 3 Enhancement: Calculate base quality score with or without faces.
        
        This method enables scoring for:
        - Portraits: Face quality (eyes open) is primary factor
        - Landscapes: Sharpness, lighting, and composition dominate
        - Architecture/Objects: Technical quality matters most
        
        Scoring Strategy:
        - WITH faces: Face quality (60%) + Technical (40%)
        - WITHOUT faces: Technical quality (100%) - Landscape Mode
        
        Technical Quality = Sharpness (30%) + Local Sharpness (20%) + Detail (15%) + Foreground/Background (10%) + Lighting (15%) + Resolution (10%)
        
        Args:
            overall_sharpness: Sharpness score (FFT 0-100 or legacy Laplacian variance)
            local_sharpness: Local sharpness consistency score (0-100)
            detail_score: Texture/detail score (0-100)
            fg_bg_score: Foreground/background separation score (0-100)
            lighting_score: Histogram-based score (0-100)
            resolution_score: Megapixel-based score (0-100)
            face_quality: Face analysis result (may be None)
            width: Image width in pixels
            height: Image height in pixels
        
        Returns:
            Combined quality score (0-100)
        """
        # Normalize sharpness to 0-100 scale
        # FFT-based sharpness already returns 0-100.
        # If a legacy Laplacian variance is passed, scale it.
        if overall_sharpness <= 100:
            sharpness_normalized = max(0.0, min(100.0, overall_sharpness))
        else:
            # Typical good images: 150-400, excellent: 300+
            # Blurry images: < 100
            sharpness_normalized = min(100, (overall_sharpness / 400) * 100)
        
        # Technical quality score (weighted average)
        technical_score = (
            sharpness_normalized * 0.30 +  # Global sharpness
            local_sharpness * 0.20 +       # Local sharpness consistency
            detail_score * 0.15 +          # Texture/detail richness
            fg_bg_score * 0.10 +           # Foreground/background separation
            lighting_score * 0.15 +        # Good exposure matters
            resolution_score * 0.10        # Resolution is bonus
        )

        # Motion blur & autofocus penalties (Week 5)
        motion_blur_penalty = self.calculate_motion_blur_penalty(
            sharpness_normalized, local_sharpness
        )
        autofocus_penalty = self.calculate_autofocus_penalty(
            sharpness_normalized, local_sharpness
        )
        technical_score = max(0.0, technical_score - motion_blur_penalty - autofocus_penalty)
        
        # Mode detection: Portrait vs Landscape
        has_faces = face_quality and face_quality.has_face
        
        if has_faces:
            # Portrait Mode: Face quality dominates
            face_score = self.calculate_face_quality_score(face_quality)
            
            # Weighted combination: 60% faces, 40% technical
            final_score = face_score * 0.60 + technical_score * 0.40
            
            logger.debug(
                f"Portrait Mode: Face={face_score:.1f} (60%), "
                f"Technical={technical_score:.1f} (40%) → {final_score:.1f}"
            )
        else:
            # Landscape Mode: Pure technical quality
            # No penalty for missing faces - landscapes are valid!
            final_score = technical_score
            
            logger.debug(
                f"Landscape Mode: Technical={technical_score:.1f} "
                f"(Sharp={sharpness_normalized:.1f}, Local={local_sharpness:.1f}, "
                f"Detail={detail_score:.1f}, FG/BG={fg_bg_score:.1f}, "
                f"Light={lighting_score:.1f}, Res={resolution_score:.1f}, "
                f"BlurPenalty={motion_blur_penalty:.1f}, AFPenalty={autofocus_penalty:.1f})"
            )
        
        return round(final_score, 2)

    def calculate_sharpness_fft(self, gray: NDArray) -> float:
        """
        Calculate sharpness using FFT high-frequency energy ratio.
        
        Returns a 0-100 score where higher means sharper.
        """
        try:
            if gray is None or gray.size == 0:
                return 0.0
            
            np = self.np
            # Compute FFT and magnitude spectrum
            f = np.fft.fft2(gray)
            fshift = np.fft.fftshift(f)
            magnitude = np.abs(fshift)
            
            if magnitude.size == 0:
                return 0.0
            
            h, w = gray.shape[:2]
            cy, cx = h // 2, w // 2
            radius = int(min(h, w) * 0.1)  # low-frequency radius
            
            # Mask for low frequencies (center circle)
            y, x = np.ogrid[:h, :w]
            mask = (y - cy) ** 2 + (x - cx) ** 2 <= radius ** 2
            
            low_freq_energy = magnitude[mask].sum()
            total_energy = magnitude.sum()
            if total_energy == 0:
                return 0.0
            
            high_freq_energy = total_energy - low_freq_energy
            ratio = high_freq_energy / total_energy
            
            # Scale to 0-100
            return float(min(100.0, max(0.0, ratio * 100.0)))
        except Exception as e:
            logger.debug(f"FFT sharpness calculation failed: {e}")
            return 0.0

    def calculate_local_sharpness(self, gray: NDArray) -> float:
        """
        Week 5: Local sharpness consistency using tile-based Laplacian.
        Returns a 0-100 score where higher means more consistently sharp.
        """
        try:
            if gray is None or gray.size == 0:
                return 0.0

            cv2 = self.cv2
            np = self.np
            
            h, w = gray.shape[:2]
            if h < 64 or w < 64:
                return self.calculate_sharpness_fft(gray)

            tiles_y = 3
            tiles_x = 3
            tile_h = h // tiles_y
            tile_w = w // tiles_x
            scores = []

            for ty in range(tiles_y):
                for tx in range(tiles_x):
                    y0 = ty * tile_h
                    x0 = tx * tile_w
                    y1 = h if ty == tiles_y - 1 else y0 + tile_h
                    x1 = w if tx == tiles_x - 1 else x0 + tile_w
                    tile = gray[y0:y1, x0:x1]
                    if tile.size == 0:
                        continue
                    var = cv2.Laplacian(tile, cv2.CV_64F).var()
                    # Normalize similar to legacy scale
                    score = min(100.0, (var / 400.0) * 100.0)
                    scores.append(score)

            if not scores:
                return self.calculate_sharpness_fft(gray)

            # Penalize inconsistency: average minus std deviation
            avg = float(np.mean(scores))
            std = float(np.std(scores))
            local_score = max(0.0, min(100.0, avg - std))

            if AppConfig.is_debug():
                logger.debug(f"LocalSharpness: avg={avg:.1f} std={std:.1f} score={local_score:.1f}")

            return local_score
        except Exception as e:
            logger.debug(f"Local sharpness calculation failed: {e}")
            return self.calculate_sharpness_fft(gray)

    def calculate_detail_score(self, gray: NDArray) -> float:
        """
        Week 5: Detail scoring using texture/edge density.
        Returns 0-100 where higher means richer detail.
        """
        try:
            if gray is None or gray.size == 0:
                return 0.0

            cv2 = self.cv2
            np = self.np
            
            # Edge density (Sobel magnitude)
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            mag = np.sqrt(grad_x ** 2 + grad_y ** 2)
            edge_strength = float(np.mean(mag))

            # Texture via Laplacian variance
            texture = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            # Normalize to 0-100
            edge_score = min(100.0, (edge_strength / 50.0) * 100.0)
            texture_score = min(100.0, (texture / 400.0) * 100.0)

            detail_score = max(0.0, min(100.0, edge_score * 0.6 + texture_score * 0.4))

            if AppConfig.is_debug():
                logger.debug(
                    f"DetailScore: edge={edge_score:.1f} texture={texture_score:.1f} "
                    f"score={detail_score:.1f}"
                )

            return detail_score
        except Exception as e:
            logger.debug(f"Detail score calculation failed: {e}")
            return 0.0

    def calculate_foreground_background_score(self, gray: NDArray) -> float:
        """
        Foreground/Background separation score based on center vs edge sharpness.
        Higher score if center is sharper than edges (subject separation).
        """
        try:
            if gray is None or gray.size == 0:
                return 0.0

            cv2 = self.cv2
            np = self.np
            
            h, w = gray.shape[:2]
            if h < 64 or w < 64:
                return 0.0

            # Define center region (subject area)
            ch, cw = int(h * 0.5), int(w * 0.5)
            y0 = (h - ch) // 2
            x0 = (w - cw) // 2
            center = gray[y0:y0 + ch, x0:x0 + cw]

            # Edge region mask (background area)
            edge_mask = np.ones_like(gray, dtype=bool)
            edge_mask[y0:y0 + ch, x0:x0 + cw] = False
            edges = gray[edge_mask]

            if center.size == 0 or edges.size == 0:
                return 0.0

            # Sharpness via Laplacian variance
            center_var = float(cv2.Laplacian(center, cv2.CV_64F).var())
            edge_var = float(cv2.Laplacian(edges, cv2.CV_64F).var())

            # Ratio of center sharpness to edge sharpness
            ratio = (center_var + 1e-6) / (edge_var + 1e-6)
            # Map ratio to 0-100 with diminishing returns
            score = min(100.0, max(0.0, (ratio - 0.5) * 40.0))

            if AppConfig.is_debug():
                logger.debug(
                    f"FG/BG: center_var={center_var:.1f} edge_var={edge_var:.1f} "
                    f"ratio={ratio:.2f} score={score:.1f}"
                )

            return score
        except Exception as e:
            logger.debug(f"Foreground/background calculation failed: {e}")
            return 0.0

    def calculate_motion_blur_penalty(
        self, sharpness_normalized: float, local_sharpness: float
    ) -> float:
        """
        Motion blur penalty (0-20). Higher when sharpness is low overall.
        """
        # Penalize strongly if global sharpness is low
        if sharpness_normalized >= 60:
            return 0.0
        # Scale penalty for low sharpness
        penalty = (60.0 - sharpness_normalized) * 0.3
        return min(20.0, max(0.0, penalty))

    def calculate_autofocus_penalty(
        self, sharpness_normalized: float, local_sharpness: float
    ) -> float:
        """
        Autofocus error penalty (0-15). Higher when local sharpness is
        much lower than global sharpness (inconsistent focus).
        """
        diff = sharpness_normalized - local_sharpness
        if diff <= 5:
            return 0.0
        penalty = diff * 0.3
        return min(15.0, max(0.0, penalty))

    def calculate_lighting_score(self, gray: NDArray) -> float:
        """Calculate lighting quality score (0-100) based on histogram analysis.
        
        BUG-L3 FIX: Comprehensive docstring explaining scoring algorithm.
        BUG-M1 FIX: Uses ScoringConstants for all threshold values.
        BUG-H3 FIX: Includes empty image/histogram protection.
        
        Evaluates three aspects of lighting quality:
        1. Brightness: Ideal range is 110-140 (slightly bright)
        2. Contrast: Good contrast has std deviation > 40
        3. Clipping: Penalizes over/underexposed pixels
        
        Scoring formula:
        - Base score: 50% brightness + 50% contrast
        - Penalty: Subtract percentage of clipped pixels (too dark/bright)
        - Range: Clamped to 0-100
        
        Args:
            gray: Grayscale image array (numpy ndarray, single channel)
            
        Returns:
            Lighting quality score (0-100)
            - 100: Perfect exposure and contrast
            - 50: Neutral (fallback for errors or empty images)
            - 0: Severely under/overexposed or no contrast
            
        Note:
            Returns 50.0 (neutral) if image is empty or histogram cannot be computed.
        """
        try:
            cv2 = self.cv2
            np = self.np
            
            # BUG-H3 FIX: Check for empty or invalid images before processing
            if gray.size == 0:
                logger.warning("Empty image array, using neutral lighting score")
                return 50.0
            
            # Calculate histogram
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            
            # BUG-H3 FIX: Check histogram sum before division to prevent division by zero
            hist_sum = hist.sum()
            if hist_sum == 0:
                logger.warning("Empty histogram (all-black image), using neutral lighting score")
                return 50.0
            
            hist = hist.flatten() / hist_sum  # Normalize
            
            # Calculate mean brightness
            mean_brightness = np.mean(gray)
            
            # Calculate contrast (std deviation)
            contrast = np.std(gray)
            
            # Ideal brightness: centered around 125 (slightly bright)
            brightness_score = 100 * (
                1 - min(
                    abs(mean_brightness - ScoringConstants.LIGHTING_IDEAL_BRIGHTNESS_CENTER) 
                    / ScoringConstants.LIGHTING_IDEAL_BRIGHTNESS_CENTER, 
                    1.0
                )
            )
            
            # Good contrast: > 40
            contrast_score = min(contrast / ScoringConstants.LIGHTING_CONTRAST_REFERENCE, 1.0) * 100
            
            # Check for clipping (over/underexposure)
            dark_pixels = np.sum(gray < ScoringConstants.LIGHTING_DARK_PIXEL_THRESHOLD) / gray.size
            bright_pixels = np.sum(gray > ScoringConstants.LIGHTING_BRIGHT_PIXEL_THRESHOLD) / gray.size
            clipping_penalty = (dark_pixels + bright_pixels) * 100
            
            # HDR/Exposure balance score (0-100)
            exposure_balance_score = self.calculate_exposure_balance(gray)

            # Combined score (Week 4: HDR/Exposure Optimization)
            lighting_score = (
                brightness_score * 0.4 +
                contrast_score * 0.4 +
                exposure_balance_score * 0.2
            ) - clipping_penalty
            lighting_score = max(0, min(100, lighting_score))
            
            # BUG-M2 FIX: Use debug level for detailed scoring (only in DEBUG mode)
            if AppConfig.is_debug():
                logger.debug(
                    f"Lighting: Brightness={mean_brightness:.1f} Contrast={contrast:.1f} "
                    f"Exposure={exposure_balance_score:.1f} Score={lighting_score:.1f}"
                )
            
            return lighting_score
        except Exception as e:
            logger.warning(f"Lighting calculation failed: {e}")
            return 50.0  # Neutral default

    def calculate_color_cast_penalty(self, bgr: NDArray) -> float:
        """
        Penalize strong color casts (overly green/blue/red tint).
        Returns a penalty (0-20) that is subtracted from lighting score.
        """
        try:
            np = self.np
            
            if bgr is None or bgr.size == 0:
                return 0.0
            # Compute mean per channel (OpenCV uses BGR)
            b_mean = float(np.mean(bgr[:, :, 0]))
            g_mean = float(np.mean(bgr[:, :, 1]))
            r_mean = float(np.mean(bgr[:, :, 2]))
            avg = (b_mean + g_mean + r_mean) / 3.0
            if avg == 0:
                return 0.0

            # Average absolute deviation from neutral gray
            deviation = (abs(b_mean - avg) + abs(g_mean - avg) + abs(r_mean - avg)) / 3.0
            deviation_ratio = deviation / avg

            # Scale to 0-20 penalty
            penalty = min(20.0, deviation_ratio * 100.0)

            if AppConfig.is_debug() and penalty > 0:
                logger.debug(
                    f"ColorCast: B={b_mean:.1f} G={g_mean:.1f} R={r_mean:.1f} "
                    f"Penalty={penalty:.1f}"
                )
            return penalty
        except Exception as e:
            logger.debug(f"Color cast calculation failed: {e}")
            return 0.0

    def calculate_exposure_balance(self, gray: NDArray) -> float:
        """
        HDR/Exposure Optimization: Evaluate shadow/highlight balance.

        Returns a 0-100 score where higher means better dynamic range usage.
        Penalizes crushed shadows and blown highlights.
        """
        try:
            np = self.np
            
            if gray is None or gray.size == 0:
                return 50.0

            # Percentiles for shadow/highlight analysis
            p5 = float(np.percentile(gray, 5))
            p50 = float(np.percentile(gray, 50))
            p95 = float(np.percentile(gray, 95))

            # Shadow penalty if very dark lower tail
            shadow_penalty = max(0.0, (20.0 - p5)) * 2.0
            # Highlight penalty if very bright upper tail
            highlight_penalty = max(0.0, (p95 - 235.0)) * 2.0

            # Midtone balance: penalize if median is too dark/bright
            midtone_penalty = abs(p50 - 128.0) * 0.2

            score = 100.0 - (shadow_penalty + highlight_penalty + midtone_penalty)
            score = max(0.0, min(100.0, score))

            if AppConfig.is_debug():
                logger.debug(
                    f"ExposureBalance: p5={p5:.1f} p50={p50:.1f} p95={p95:.1f} "
                    f"Score={score:.1f}"
                )

            return score
        except Exception as e:
            logger.debug(f"Exposure balance calculation failed: {e}")
            return 50.0

    def normalize_face_sharpness_score(self, face_sharpness: float) -> float:
        """Normalize face sharpness to a 0-100 score."""
        if face_sharpness <= 0:
            return 0.0
        reference = ScoringConstants.SHARPNESS_REFERENCE_FACE_AREA
        return max(0.0, min(100.0, (face_sharpness / reference) * 100.0))

    def calculate_eye_openness_score(self, landmarks) -> float:
        """Return eye openness score (0-100) using EAR."""
        left_top = landmarks[159].y
        left_bottom = landmarks[145].y
        right_top = landmarks[386].y
        right_bottom = landmarks[374].y
        ear = (abs(left_top - left_bottom) + abs(right_top - right_bottom)) / 2.0
        score = (ear - ScoringConstants.EAR_SCORE_MIN) / (
            ScoringConstants.EAR_SCORE_MAX - ScoringConstants.EAR_SCORE_MIN
        )
        return max(0.0, min(100.0, score * 100.0))

    def calculate_gaze_score(self, landmarks) -> float:
        """Return eye contact score (0-100) based on iris centering."""
        left_iris = landmarks[468].x if len(landmarks) > 468 else landmarks[33].x
        left_inner = landmarks[133].x
        left_outer = landmarks[33].x
        right_iris = landmarks[473].x if len(landmarks) > 473 else landmarks[362].x
        right_inner = landmarks[362].x
        right_outer = landmarks[263].x

        left_center = (left_inner + left_outer) / 2.0
        right_center = (right_inner + right_outer) / 2.0
        left_dev = abs(left_iris - left_center)
        right_dev = abs(right_iris - right_center)
        avg_dev = (left_dev + right_dev) / 2.0

        score = 1.0 - (avg_dev / ScoringConstants.GAZE_MAX_DEVIATION)
        return max(0.0, min(100.0, score * 100.0))

    def calculate_head_pose_score(self, landmarks) -> float:
        """Return head pose score (0-100) based on tilt and yaw proxies."""
        nose_top = landmarks[168]
        nose_bottom = landmarks[2]
        left_cheek = landmarks[234]
        right_cheek = landmarks[454]

        nose_angle = abs(nose_top.x - nose_bottom.x)
        face_tilt = abs(left_cheek.y - right_cheek.y)
        deviation = max(nose_angle, face_tilt)
        score = 1.0 - (deviation / ScoringConstants.HEAD_TILT_MAX_DEVIATION)
        return max(0.0, min(100.0, score * 100.0))

    def calculate_smile_score(self, landmarks) -> float:
        """Return smile score (0-100) using mouth aspect ratio."""
        left_corner = landmarks[61]
        right_corner = landmarks[291]
        upper_lip = landmarks[13]
        lower_lip = landmarks[14]

        mouth_width = abs(left_corner.x - right_corner.x)
        mouth_height = abs(upper_lip.y - lower_lip.y)
        ratio = mouth_width / (mouth_height + 1e-6)

        score = (ratio - ScoringConstants.SMILE_RATIO_MIN) / (
            ScoringConstants.SMILE_RATIO_MAX - ScoringConstants.SMILE_RATIO_MIN
        )
        return max(0.0, min(100.0, score * 100.0))

    def select_best_person(self, person_statuses: list[PersonEyeStatus]) -> Optional[PersonEyeStatus]:
        """Select best person among multiple faces based on quality signals."""
        if not person_statuses:
            return None

        max_face_size = max(p.face_size_pixels for p in person_statuses) or 1

        def score_person(ps: PersonEyeStatus) -> float:
            size_score = ps.face_size_pixels / max_face_size
            confidence_score = ps.face_confidence
            eyes_score = (
                ps.eyes_open_score / 100.0
                if ps.eyes_open_score is not None
                else (1.0 if ps.eyes_open else 0.3)
            )
            sharpness_score = (
                self.normalize_face_sharpness_score(ps.face_sharpness) / 100.0
                if ps.face_sharpness is not None
                else 0.0
            )
            gaze_score = (ps.gaze_score / 100.0) if ps.gaze_score is not None else 0.5
            head_score = (ps.head_pose_score / 100.0) if ps.head_pose_score is not None else 0.5
            smile_score = (ps.smile_score / 100.0) if ps.smile_score is not None else 0.5

            return (
                size_score * 0.25
                + confidence_score * 0.15
                + eyes_score * 0.25
                + sharpness_score * 0.15
                + gaze_score * 0.10
                + head_score * 0.10
                + smile_score * 0.10
            )

        return max(person_statuses, key=score_person)

    def calculate_face_quality_score(self, face_quality: FaceQuality) -> float:
        """Calculate face-based score (0-100) using detailed face metrics."""
        if not face_quality or not face_quality.has_face:
            return ScoringConstants.FACE_QUALITY_NO_FACE_NEUTRAL

        eye_score = (
            face_quality.eye_open_score
            if face_quality.eye_open_score is not None
            else (100.0 if face_quality.all_eyes_open else ScoringConstants.FACE_QUALITY_CLOSED_EYES_MALUS)
        )
        sharpness_score = self.normalize_face_sharpness_score(face_quality.face_sharpness)
        gaze_score = face_quality.gaze_forward_score
        head_pose_score = face_quality.head_pose_score
        smile_score = face_quality.smile_score

        scores = {
            "eyes": eye_score,
            "sharpness": sharpness_score,
            "gaze": gaze_score,
            "head_pose": head_pose_score,
            "smile": smile_score,
        }
        weights = {
            "eyes": ScoringConstants.FACE_SCORE_WEIGHT_EYES,
            "sharpness": ScoringConstants.FACE_SCORE_WEIGHT_SHARPNESS,
            "gaze": ScoringConstants.FACE_SCORE_WEIGHT_GAZE,
            "head_pose": ScoringConstants.FACE_SCORE_WEIGHT_HEAD_POSE,
            "smile": ScoringConstants.FACE_SCORE_WEIGHT_SMILE,
        }

        total_weight = 0.0
        weighted_sum = 0.0
        for key, value in scores.items():
            if value is None:
                continue
            weighted_sum += value * weights[key]
            total_weight += weights[key]

        if total_weight == 0.0:
            face_score = ScoringConstants.FACE_QUALITY_BASE_SCORE
        else:
            face_score = weighted_sum / total_weight

        if not face_quality.all_eyes_open:
            face_score = min(face_score, ScoringConstants.FACE_QUALITY_CLOSED_EYES_MALUS)

        face_score = min(100.0, face_score + face_quality.confidence * ScoringConstants.FACE_QUALITY_CONFIDENCE_BOOST)
        return max(0.0, min(100.0, face_score))

    def check_eyes_open(self, landmarks) -> bool:
        """
        Check if eyes are open using Eye Aspect Ratio.
        
        MediaPipe Face Mesh landmark indices:
        - Left eye: 33, 160, 158, 133, 153, 144
        - Right eye: 362, 385, 387, 263, 373, 380
        """
        # Left eye vertical distances
        left_top = landmarks[159].y
        left_bottom = landmarks[145].y
        left_ear = abs(left_top - left_bottom)
        
        # Right eye vertical distances
        right_top = landmarks[386].y
        right_bottom = landmarks[374].y
        right_ear = abs(right_top - right_bottom)
        
        # Average EAR
        ear = (left_ear + right_ear) / 2
        
        # Threshold (typical open eye has EAR > 0.02)
        return ear > ScoringConstants.EAR_THRESHOLD_MEDIAPIPE
    
    def check_gaze_forward(self, landmarks) -> bool:
        """
        Check if gaze is forward (not looking away).
        
        Uses iris positions relative to eye corners.
        """
        # Left iris center (landmark 468)
        left_iris = landmarks[468].x if len(landmarks) > 468 else landmarks[33].x
        left_inner = landmarks[133].x
        left_outer = landmarks[33].x
        
        # Right iris center (landmark 473)
        right_iris = landmarks[473].x if len(landmarks) > 473 else landmarks[362].x
        right_inner = landmarks[362].x
        right_outer = landmarks[263].x
        
        # Check if iris is centered (with tolerance)
        left_centered = abs(left_iris - (left_inner + left_outer) / 2) < ScoringConstants.GAZE_CENTER_TOLERANCE
        right_centered = abs(right_iris - (right_inner + right_outer) / 2) < ScoringConstants.GAZE_CENTER_TOLERANCE
        
        return left_centered and right_centered
    
    def check_head_straight(self, landmarks) -> bool:
        """
        Check if head is straight (not tilted).
        
        Uses nose bridge and face outline angles.
        """
        # Nose bridge points
        nose_top = landmarks[168]
        nose_bottom = landmarks[2]
        
        # Face outline points
        left_cheek = landmarks[234]
        right_cheek = landmarks[454]
        
        # Calculate angles
        nose_angle = abs(nose_top.x - nose_bottom.x)
        face_tilt = abs(left_cheek.y - right_cheek.y)
        
        # Threshold for straightness
        return nose_angle < ScoringConstants.HEAD_TILT_ANGLE_TOLERANCE and face_tilt < ScoringConstants.HEAD_TILT_ANGLE_TOLERANCE
    
    def calculate_face_sharpness(
        self, img: NDArray, landmarks, width: int, height: int
    ) -> float:
        """
        Calculate sharpness in face region.
        
        Args:
            img: OpenCV image
            landmarks: Face landmarks
            width: Image width
            height: Image height
            
        Returns:
            Sharpness score (Laplacian variance, normalized by region area)
        """
        cv2 = self.cv2
        np = self.np
        
        # Get face bounding box
        x_coords = [lm.x * width for lm in landmarks]
        y_coords = [lm.y * height for lm in landmarks]
        
        x_min = max(0, int(min(x_coords)) - 20)
        x_max = min(width, int(max(x_coords)) + 20)
        y_min = max(0, int(min(y_coords)) - 20)
        y_max = min(height, int(max(y_coords)) + 20)
        
        # Extract face region
        face_region = img[y_min:y_max, x_min:x_max]
        
        if face_region.size == 0:
            return 0.0
        
        # Calculate sharpness in face region
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray_face, cv2.CV_64F)
        variance = laplacian.var()
        
        # BUGFIX: Normalize by region area to make dimension-independent
        # Without this, portrait and landscape faces get different scores
        # even with identical sharpness due to different aspect ratios.
        # 
        # Explanation: Laplacian variance is affected by edge distribution
        # across the region. A 500×700 region produces different variance
        # than a 700×500 region (same area, different proportions).
        # 
        # Normalization formula: var * sqrt(area / reference_area)
        # Reference: 500×500 = 250,000 pixels (typical face region)
        region_area = face_region.shape[0] * face_region.shape[1]
        reference_area = ScoringConstants.SHARPNESS_REFERENCE_FACE_AREA
        normalization_factor = np.sqrt(region_area / reference_area)
        
        sharpness = variance * normalization_factor
        
        return sharpness
