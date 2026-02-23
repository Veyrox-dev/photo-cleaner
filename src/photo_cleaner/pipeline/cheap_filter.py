"""
Cheap Filter Module

Fast, deterministic filtering without AI.
Removes low-quality images before expensive analysis.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Lazy load cv2 and numpy to avoid PyInstaller frozen module issues
_cv2 = None
_np = None
CV2_AVAILABLE = True

def _get_cv2():
    """Lazy load cv2 - delays numpy initialization in frozen environment."""
    global _cv2, _np, CV2_AVAILABLE
    if _cv2 is None:
        try:
            import cv2
            import numpy as np
            _cv2 = cv2
            _np = np
            CV2_AVAILABLE = True
        except ImportError:
            CV2_AVAILABLE = False
            _cv2 = None
            _np = None
    return _cv2, _np

from PIL import Image

# Register HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # pillow-heif not available, HEIC files will fail

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of cheap filter analysis."""
    
    passed: bool
    reason: Optional[str] = None
    resolution: Optional[tuple[int, int]] = None
    sharpness_score: Optional[float] = None
    brightness_score: Optional[float] = None


class CheapFilter:
    """
    Fast, cheap quality filters without face detection.
    
    Filters out:
    - Images with too low resolution
    - Extremely blurry images
    - Heavily under- or overexposed images
    """
    
    def __init__(
        self,
        min_width: int = 800,
        min_height: int = 600,
        sharpness_threshold: float = 50.0,
        brightness_low: float = 30.0,
        brightness_high: float = 225.0,
    ):
        """
        Initialize cheap filter.
        
        Args:
            min_width: Minimum image width
            min_height: Minimum image height
            sharpness_threshold: Minimum Laplacian variance for sharpness
            brightness_low: Minimum acceptable mean brightness (0-255)
            brightness_high: Maximum acceptable mean brightness (0-255)
        """
        self.min_width = min_width
        self.min_height = min_height
        self.sharpness_threshold = sharpness_threshold
        self.brightness_low = brightness_low
        self.brightness_high = brightness_high
    
    def analyze_image(self, image_path: Path) -> FilterResult:
        """
        Analyze single image with cheap filters.
        
        Args:
            image_path: Path to image file
            
        Returns:
            FilterResult with pass/fail and metrics
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available, skipping cheap filter analysis")
            return FilterResult(
                passed=True,
                reason="OpenCV not installed - filter skipped",
            )
        
        cv2, np = _get_cv2()
        if cv2 is None:
            return FilterResult(
                passed=True,
                reason="OpenCV not available at runtime",
            )
        
        try:
            # Check resolution with PIL (fast)
            with Image.open(image_path) as pil_img:
                width, height = pil_img.size
                
                if width < self.min_width or height < self.min_height:
                    return FilterResult(
                        passed=False,
                        reason=f"Resolution too low: {width}x{height}",
                        resolution=(width, height),
                    )
                
                # Convert to grayscale directly to avoid extra color conversions
                if pil_img.mode != "L":
                    pil_img = pil_img.convert("L")
                gray = np.asarray(pil_img)
            
            # Check sharpness (Laplacian variance)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Normalize by image area (larger images have lower variance)
            # Reference: 1920×1080 = 2,073,600 pixels
            image_area = width * height
            reference_area = 2_073_600  # Full HD reference
            normalization_factor = np.sqrt(image_area / reference_area)
            normalized_sharpness = laplacian_var * normalization_factor
            
            logger.debug(
                f"CheapFilter: {image_path.name} → {width}×{height} = {image_area/1_000_000:.1f}MP, "
                f"raw_sharpness={laplacian_var:.1f}, normalized={normalized_sharpness:.1f}, threshold={self.sharpness_threshold}"
            )
            
            if normalized_sharpness < self.sharpness_threshold:
                return FilterResult(
                    passed=False,
                    reason=f"Too blurry: {normalized_sharpness:.1f}",
                    resolution=(width, height),
                    sharpness_score=normalized_sharpness,
                )
            
            # Check brightness (mean pixel value)
            brightness = float(gray.mean())
            
            if brightness < self.brightness_low:
                return FilterResult(
                    passed=False,
                    reason=f"Too dark: {brightness:.1f}",
                    resolution=(width, height),
                    sharpness_score=normalized_sharpness,
                    brightness_score=brightness,
                )
            
            if brightness > self.brightness_high:
                return FilterResult(
                    passed=False,
                    reason=f"Too bright: {brightness:.1f}",
                    resolution=(width, height),
                    sharpness_score=normalized_sharpness,
                    brightness_score=brightness,
                )
            
            # Passed all checks
            return FilterResult(
                passed=True,
                resolution=(width, height),
                sharpness_score=normalized_sharpness,
                brightness_score=brightness,
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze {image_path}: {e}")
            return FilterResult(
                passed=False,
                reason=f"Analysis error: {e}",
            )
    
    def filter_batch(self, image_paths: list[Path]) -> dict[Path, FilterResult]:
        """
        Filter multiple images.
        
        Args:
            image_paths: List of image paths
            
        Returns:
            Dict mapping path to FilterResult
        """
        results: dict[Path, FilterResult] = {}
        if not image_paths:
            return results

        max_workers = min(4, os.cpu_count() or 1)
        if max_workers <= 1 or len(image_paths) < 4:
            for path in image_paths:
                results[path] = self.analyze_image(path)
            return results

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.analyze_image, path): path
                for path in image_paths
            }
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    results[path] = future.result()
                except Exception as e:
                    logger.warning(f"Failed to analyze {path}: {e}")
                    results[path] = FilterResult(
                        passed=False,
                        reason=f"Analysis error: {e}",
                    )

        return results
