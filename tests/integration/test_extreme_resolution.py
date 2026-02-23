"""
TEST-1: Extreme Resolution Test Suite

Covers edge cases with extremely low and extremely high resolutions
for AutoSelector scoring. Ensures scores are clamped and no crashes occur.
"""

from pathlib import Path

from photo_cleaner.pipeline.auto_selector import AutoSelector


def test_extreme_resolution_scores_are_clamped():
    selector = AutoSelector()

    image_small = Path("small.jpg")
    image_large = Path("large.jpg")

    quality_data_small = {
        "sharpness_score": 200.0,
        "lighting_score": 50.0,
        "resolution": (1, 1),  # 1x1 pixel
        "face_quality": None,
        "camera_model": "unknown",
        "exif_data": {},
    }

    quality_data_large = {
        "sharpness_score": 200.0,
        "lighting_score": 50.0,
        "resolution": (100000, 100000),  # 10^10 pixels
        "face_quality": None,
        "camera_model": "unknown",
        "exif_data": {},
    }

    score_small = selector._score_image(image_small, quality_data_small)
    score_large = selector._score_image(image_large, quality_data_large)

    assert 0 <= score_small.resolution_score <= 100
    assert 0 <= score_large.resolution_score <= 100
    assert 0 <= score_small.sharpness_score <= 100
    assert 0 <= score_large.sharpness_score <= 100


def test_extreme_resolution_group_selection_does_not_crash():
    selector = AutoSelector()

    image_small = Path("small.jpg")
    image_large = Path("large.jpg")

    quality_results = {
        image_small: {
            "sharpness_score": 200.0,
            "lighting_score": 50.0,
            "resolution": (1, 1),
            "face_quality": None,
            "camera_model": "unknown",
            "exif_data": {},
        },
        image_large: {
            "sharpness_score": 200.0,
            "lighting_score": 50.0,
            "resolution": (100000, 100000),
            "face_quality": None,
            "camera_model": "unknown",
            "exif_data": {},
        },
    }

    best, score = selector.select_best_image([image_small, image_large], quality_results)
    assert best in (image_small, image_large)
    assert score is not None
