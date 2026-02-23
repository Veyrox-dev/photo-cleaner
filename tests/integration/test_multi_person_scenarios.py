"""
TEST-3: Multi-Person Scenario Tests

Validates face-quality scoring when multiple people are detected.
Ensures all_eyes_open logic applies correct malus.
"""

from pathlib import Path

from photo_cleaner.pipeline.auto_selector import AutoSelector
from photo_cleaner.pipeline.quality_analyzer import FaceQuality, PersonEyeStatus
from photo_cleaner.pipeline.scoring_constants import ScoringConstants


def test_multi_person_closed_eyes_malus_applied():
    selector = AutoSelector()
    image_path = Path("group_photo.jpg")

    face_quality = FaceQuality(
        has_face=True,
        all_eyes_open=False,
        confidence=0.9,
        num_faces=2,
        person_eye_statuses=[
            PersonEyeStatus(person_id=1, eyes_open=True, face_confidence=0.9, face_size_pixels=10000),
            PersonEyeStatus(person_id=2, eyes_open=False, face_confidence=0.8, face_size_pixels=9000),
        ],
    )

    quality_data = {
        "sharpness_score": 300.0,
        "lighting_score": 60.0,
        "resolution": (4000, 3000),
        "face_quality": face_quality,
        "camera_model": "unknown",
        "exif_data": {},
    }

    score = selector._score_image(image_path, quality_data)
    assert score.face_quality_score == ScoringConstants.FACE_QUALITY_CLOSED_EYES_MALUS


def test_multi_person_all_eyes_open_bonus_applied():
    selector = AutoSelector()
    image_path = Path("group_photo_open.jpg")

    face_quality = FaceQuality(
        has_face=True,
        all_eyes_open=True,
        confidence=0.8,
        num_faces=3,
        person_eye_statuses=[
            PersonEyeStatus(person_id=1, eyes_open=True, face_confidence=0.9, face_size_pixels=11000),
            PersonEyeStatus(person_id=2, eyes_open=True, face_confidence=0.85, face_size_pixels=10000),
            PersonEyeStatus(person_id=3, eyes_open=True, face_confidence=0.8, face_size_pixels=9500),
        ],
    )

    quality_data = {
        "sharpness_score": 300.0,
        "lighting_score": 60.0,
        "resolution": (4000, 3000),
        "face_quality": face_quality,
        "camera_model": "unknown",
        "exif_data": {},
    }

    score = selector._score_image(image_path, quality_data)
    expected_min = ScoringConstants.FACE_QUALITY_BASE_SCORE
    assert score.face_quality_score >= expected_min
