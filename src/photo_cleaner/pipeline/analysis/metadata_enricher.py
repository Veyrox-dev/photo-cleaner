from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from photo_cleaner.pipeline.analysis.models import CameraProfile


@dataclass
class EnrichedImageMetadata:
    img: Any
    width: int
    height: int
    resolution_score: float
    camera_model: str
    exif_data: dict
    iso_value: Any
    aperture_value: Any
    focal_length: Any
    exposure_time: Any


def enrich_image_with_metadata(
    image_path: Path,
    *,
    img,
    pil_img,
    original_width: int,
    original_height: int,
    exif_extractor,
    logger=None,
) -> EnrichedImageMetadata:
    """Apply EXIF orientation and collect scoring-relevant metadata for analysis."""
    exif_orientation = exif_extractor.get_exif_orientation_from_pil(pil_img, image_path)
    if exif_orientation != 1:
        if logger:
            logger.debug(f"  [BUG-C2 FIX] Applying EXIF rotation: {exif_orientation}")
        img = exif_extractor.rotate_image_from_exif(img, exif_orientation)

    exif_data = exif_extractor.extract_exif_data_from_pil(pil_img, image_path)
    camera_model = CameraProfile.extract_camera_model(exif_data)

    iso_value = exif_data.get("iso_value")
    aperture_value = exif_data.get("aperture_value")
    focal_length = exif_data.get("focal_length")
    exposure_time = exif_data.get("exposure_time")

    height, width = img.shape[:2]
    resolution_score = (original_width * original_height) / 1_000_000

    orientation = "Portrait" if original_height > original_width else "Landscape"
    if logger:
        if width != original_width or height != original_height:
            logger.debug(
                f"QualityAnalyzer: {image_path.name} → {orientation} "
                f"{original_width}×{original_height} = {resolution_score:.1f}MP "
                f"(analyzing at {width}×{height})"
            )
        else:
            logger.debug(
                f"QualityAnalyzer: {image_path.name} → {orientation} "
                f"{width}×{height} = {resolution_score:.1f}MP"
            )

    return EnrichedImageMetadata(
        img=img,
        width=width,
        height=height,
        resolution_score=resolution_score,
        camera_model=camera_model,
        exif_data=exif_data,
        iso_value=iso_value,
        aperture_value=aperture_value,
        focal_length=focal_length,
        exposure_time=exposure_time,
    )
