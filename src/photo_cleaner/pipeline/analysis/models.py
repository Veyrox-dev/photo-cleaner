from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CameraProfile:
    """Camera-specific calibration for fair scoring across devices."""

    PROFILE_SHARPNESS_FACTOR = {
        "iPhone": 1.0,
        "Samsung": 1.2,
        "Pixel": 1.3,
        "OnePlus": 1.1,
        "Xiaomi": 1.15,
        "Huawei": 1.1,
        "Motorola": 1.05,
        "LG": 1.08,
        "unknown": 1.0,
        "default": 1.0,
    }

    PROFILE_RESOLUTION_FACTOR = {
        "iPhone": {"iPhone-12": 12.0, "iPhone-13": 12.0, "iPhone-14": 12.0, "iPhone-15": 12.0, "default": 12.0},
        "Samsung": {"S20": 12.0, "S21": 12.0, "S22": 50.0, "S23": 50.0, "S24": 50.0, "default": 12.0},
        "Pixel": {"Pixel-4": 12.0, "Pixel-5": 12.0, "Pixel-6": 12.0, "Pixel-7": 12.0, "Pixel-8": 12.0, "default": 12.0},
        "default": 12.0,
    }

    DYNAMIC_DATABASE = {}

    @staticmethod
    def extract_camera_model(exif_data: dict) -> str:
        if not exif_data:
            return "unknown"

        model = exif_data.get("Model", "").upper()
        make = exif_data.get("Make", "").upper()
        full_model_name = f"{make}_{model}".strip("_")

        if "IPHONE" in model or "IPHONE" in make:
            camera_model = "iPhone"
        elif "SAMSUNG" in model or "SAMSUNG" in make:
            camera_model = "Samsung"
        elif "PIXEL" in model or "PIXEL" in make:
            camera_model = "Pixel"
        elif "ONEPLUS" in model or "ONEPLUS" in make:
            camera_model = "OnePlus"
        elif "XIAOMI" in model or "XIAOMI" in make:
            camera_model = "Xiaomi"
        elif "HUAWEI" in model or "HUAWEI" in make:
            camera_model = "Huawei"
        elif "MOTOROLA" in model or "MOTOROLA" in make:
            camera_model = "Motorola"
        elif "LG" in model or "LG" in make:
            camera_model = "LG"
        else:
            camera_model = "unknown"

        if full_model_name and camera_model != "unknown":
            CameraProfile._register_dynamic_camera(full_model_name, camera_model)

        return camera_model

    @staticmethod
    def _register_dynamic_camera(full_model_name: str, camera_type: str) -> None:
        import time

        if full_model_name in CameraProfile.DYNAMIC_DATABASE:
            return

        CameraProfile.DYNAMIC_DATABASE[full_model_name] = {
            "camera_type": camera_type,
            "generation": "auto-detected",
            "first_seen": int(time.time()),
            "keep_rate": 0.5,
            "sample_count": 0,
        }

        logger.info(
            f"[PHASE-4] Dynamic database: Registered new camera '{full_model_name}' "
            f"(type: {camera_type})"
        )

    @staticmethod
    def get_dynamic_cameras() -> dict:
        return CameraProfile.DYNAMIC_DATABASE.copy()

    @staticmethod
    def get_sharpness_factor(camera_model: str) -> float:
        return CameraProfile.PROFILE_SHARPNESS_FACTOR.get(
            camera_model,
            CameraProfile.PROFILE_SHARPNESS_FACTOR["default"],
        )

    @staticmethod
    def get_resolution_baseline(camera_model: str, model_name: str = None) -> float:
        if camera_model not in CameraProfile.PROFILE_RESOLUTION_FACTOR:
            return CameraProfile.PROFILE_RESOLUTION_FACTOR["default"]

        profiles = CameraProfile.PROFILE_RESOLUTION_FACTOR[camera_model]
        if model_name and model_name in profiles:
            return profiles[model_name]

        return profiles.get("default", 12.0)


@dataclass
class PersonEyeStatus:
    """Status of eyes for a single detected person."""

    person_id: int
    eyes_open: bool
    face_confidence: float
    face_size_pixels: int
    face_sharpness: float = 0.0
    eyes_open_score: Optional[float] = None
    gaze_score: Optional[float] = None
    head_pose_score: Optional[float] = None
    smile_score: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "person_id": self.person_id,
            "eyes_open": self.eyes_open,
            "face_confidence": self.face_confidence,
            "face_size_pixels": self.face_size_pixels,
            "face_sharpness": self.face_sharpness,
            "eyes_open_score": self.eyes_open_score,
            "gaze_score": self.gaze_score,
            "head_pose_score": self.head_pose_score,
            "smile_score": self.smile_score,
        }

    @staticmethod
    def from_dict(data: dict) -> "PersonEyeStatus":
        return PersonEyeStatus(
            person_id=data.get("person_id", 0),
            eyes_open=data.get("eyes_open", False),
            face_confidence=data.get("face_confidence", 0.0),
            face_size_pixels=data.get("face_size_pixels", 0),
            face_sharpness=data.get("face_sharpness", 0.0),
            eyes_open_score=data.get("eyes_open_score"),
            gaze_score=data.get("gaze_score"),
            head_pose_score=data.get("head_pose_score"),
            smile_score=data.get("smile_score"),
        )


@dataclass
class FaceQuality:
    """Face quality metrics from MediaPipe Face Mesh."""

    has_face: bool
    eyes_open: bool = False
    gaze_forward: bool = False
    head_straight: bool = False
    face_sharpness: float = 0.0
    confidence: float = 0.0
    num_faces: int = 0
    eye_count: int = 0
    face_count: int = 0
    all_eyes_open: bool = False
    person_eye_statuses: list = None
    best_person_id: int = 0
    eye_open_score: Optional[float] = None
    gaze_forward_score: Optional[float] = None
    head_pose_score: Optional[float] = None
    smile_score: Optional[float] = None

    def __post_init__(self):
        if self.person_eye_statuses is None:
            self.person_eye_statuses = []


@dataclass
class QualityResult:
    """Complete quality analysis result."""

    path: Path
    face_quality: Optional[FaceQuality] = None
    overall_sharpness: float = 0.0
    lighting_score: float = 0.0
    resolution_score: float = 0.0
    width: int = 0
    height: int = 0
    total_score: float = 0.0
    error: Optional[str] = None
    camera_model: str = "unknown"
    exif_data: Optional[dict] = None
    iso_value: Optional[int] = None
    aperture_value: Optional[float] = None
    focal_length: Optional[float] = None
    exposure_time: Optional[float] = None
