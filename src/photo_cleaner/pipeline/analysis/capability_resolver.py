"""Capability resolution helpers for quality analyzer eye-detection stages."""
from __future__ import annotations

from typing import Any


def determine_available_eye_stage(
    requested_stage: int,
    *,
    cv2_available: bool,
    dlib_available: bool,
    mediapipe_available: bool,
    logger: Any,
) -> int:
    """Resolve requested stage to highest available stage based on dependencies."""
    requested_stage = max(1, min(3, requested_stage))

    if requested_stage >= 3:
        if mediapipe_available and cv2_available:
            return 3
        if not mediapipe_available:
            logger.debug("MediaPipe nicht verfuegbar, falle zurueck auf Stufe 2")

    if requested_stage >= 2:
        if dlib_available and cv2_available:
            return 2
        if not dlib_available:
            logger.debug("dlib nicht verfuegbar, falle zurueck auf Stufe 1")

    if cv2_available:
        return 1

    logger.warning("OpenCV nicht verfuegbar, Augenerkennung deaktiviert")
    return 0


def build_stage_info(
    *,
    current_stage: int,
    cv2_available: bool,
    dlib_available: bool,
    mediapipe_available: bool,
    mtcnn_available: bool,
    face_detector: str,
) -> dict[str, Any]:
    """Build UI-friendly capability summary for active eye/face detection setup."""
    available_stages: list[int] = []
    if cv2_available:
        available_stages.append(1)
    if dlib_available and cv2_available:
        available_stages.append(2)
    if mediapipe_available and cv2_available:
        available_stages.append(3)

    missing_stage_2: list[str] = []
    if not cv2_available:
        missing_stage_2.append("opencv-python")
    if not dlib_available:
        missing_stage_2.append("dlib")

    missing_stage_3: list[str] = []
    if not cv2_available:
        missing_stage_3.append("opencv-python")
    if not mediapipe_available:
        missing_stage_3.append("mediapipe")

    return {
        "current_stage": current_stage,
        "available_stages": available_stages,
        "missing_for_stage_2": missing_stage_2,
        "missing_for_stage_3": missing_stage_3,
        "mtcnn_available": mtcnn_available,
        "face_detector": face_detector,
        "face_detector_active": "mtcnn" if (face_detector == "mtcnn" and mtcnn_available) else "haar",
    }
