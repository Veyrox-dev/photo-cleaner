"""
TEST-2: No-EXIF Integration Tests

Validates behavior when images contain no EXIF data.
Ensures camera model falls back to 'unknown' and scoring remains stable.
"""

import tempfile
from pathlib import Path

from PIL import Image

from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer, CameraProfile
from photo_cleaner.pipeline.auto_selector import AutoSelector


def test_no_exif_returns_unknown_camera_model():
    analyzer = QualityAnalyzer(use_face_mesh=False)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        image_path = Path(temp_file.name)

    try:
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        img.save(image_path)

        exif_data = analyzer._extract_exif_data(image_path)
        assert exif_data == {}

        camera_model = CameraProfile.extract_camera_model(exif_data)
        assert camera_model == "unknown"
    finally:
        image_path.unlink(missing_ok=True)


def test_scoring_without_exif_is_stable():
    selector = AutoSelector()
    image_path = Path("no_exif.jpg")

    quality_data = {
        "sharpness_score": 250.0,
        "lighting_score": 60.0,
        "resolution": (4000, 3000),
        "face_quality": None,
        "camera_model": "unknown",
        # EXIF missing
    }

    score = selector._score_image(image_path, quality_data)
    assert 0 <= score.sharpness_score <= 100
    assert 0 <= score.total_score <= 100
