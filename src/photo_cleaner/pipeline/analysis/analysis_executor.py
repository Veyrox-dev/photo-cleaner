from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from photo_cleaner.pipeline.analysis.models import FaceQuality


@dataclass
class AnalysisExecutionResult:
    face_quality: FaceQuality
    overall_sharpness: float
    lighting_score: float
    total_score: float


def execute_quality_analysis(
    *,
    img,
    width: int,
    height: int,
    resolution_score: float,
    cv2_module,
    quality_scorer,
    face_detector,
    image_name: str,
    logger=None,
) -> AnalysisExecutionResult:
    """Run the core quality analysis execution (gray metrics + face + final score)."""
    gray = cv2_module.cvtColor(img, cv2_module.COLOR_BGR2GRAY)
    overall_sharpness = quality_scorer.calculate_sharpness_fft(gray)
    local_sharpness = quality_scorer.calculate_local_sharpness(gray)
    detail_score = quality_scorer.calculate_detail_score(gray)
    fg_bg_score = quality_scorer.calculate_foreground_background_score(gray)

    lighting_score = quality_scorer.calculate_lighting_score(gray)
    lighting_score = max(0.0, lighting_score - quality_scorer.calculate_color_cast_penalty(img))

    try:
        face_quality = face_detector.analyze_faces(img)
    except Exception:
        if logger:
            logger.exception(f"Face analysis failed for {image_name}")
        face_quality = FaceQuality(has_face=False)

    total_score = quality_scorer.calculate_base_score(
        overall_sharpness=overall_sharpness,
        local_sharpness=local_sharpness,
        detail_score=detail_score,
        fg_bg_score=fg_bg_score,
        lighting_score=lighting_score,
        resolution_score=resolution_score,
        face_quality=face_quality,
        width=width,
        height=height,
    )

    return AnalysisExecutionResult(
        face_quality=face_quality,
        overall_sharpness=overall_sharpness,
        lighting_score=lighting_score,
        total_score=total_score,
    )
