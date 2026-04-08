from photo_cleaner.ui.group_confidence import (
    build_group_diagnostics,
    classify_group_confidence,
    compute_file_confidence_bucket,
)


def test_compute_file_confidence_bucket_high() -> None:
    bucket = compute_file_confidence_bucket(
        quality_score=88.0,
        sharpness_score=92.0,
        lighting_score=80.0,
        resolution_score=85.0,
        face_quality_score=78.0,
    )

    assert bucket == 100


def test_compute_file_confidence_bucket_low_for_multiple_concerns() -> None:
    bucket = compute_file_confidence_bucket(
        quality_score=62.0,
        sharpness_score=82.0,
        lighting_score=40.0,
        resolution_score=70.0,
        face_quality_score=28.0,
    )

    assert bucket == 25


def test_compute_file_confidence_bucket_incomplete_legacy() -> None:
    bucket = compute_file_confidence_bucket(
        quality_score=70.0,
        sharpness_score=None,
        lighting_score=None,
        resolution_score=None,
        face_quality_score=None,
    )

    assert bucket == 10


def test_classify_group_confidence_levels() -> None:
    assert classify_group_confidence(100) == "high"
    assert classify_group_confidence(65) == "medium"
    assert classify_group_confidence(25) == "low"
    assert classify_group_confidence(10) == "incomplete"
    assert classify_group_confidence(0) == "none"


def test_build_group_diagnostics_reports_patterns() -> None:
    diagnostics = build_group_diagnostics(
        weak_sharpness=1,
        weak_lighting=4,
        weak_resolution=2,
        weak_face=3,
        strong_sharpness=5,
        strong_lighting=2,
        strong_resolution=1,
        strong_face=2,
    )

    assert "Treiber-Muster: Schaerfe (5)" in diagnostics
    assert "Schwachstellen-Muster: Belichtung (4)" in diagnostics
