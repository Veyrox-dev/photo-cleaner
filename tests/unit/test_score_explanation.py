from photo_cleaner.ui.score_explanation import build_score_explanation


def test_build_score_explanation_marks_high_confidence() -> None:
    explanation = build_score_explanation(
        quality_score=84.2,
        sharpness_score=88.0,
        lighting_score=77.0,
        resolution_score=82.0,
        face_quality_score=79.0,
    )

    assert explanation.has_any_data is True
    assert explanation.confidence_label == "Sicher"
    assert explanation.confidence_level == "high"
    assert explanation.strengths_text == "Gut: Schaerfe, Belichtung, Aufloesung, Augen"
    assert explanation.concerns_text is None
    assert explanation.component_summary_text == "Treiber: Schaerfe 88% | Schwaechste Stelle: Belichtung 77%"


def test_build_score_explanation_marks_low_confidence_with_concerns() -> None:
    explanation = build_score_explanation(
        quality_score=41.0,
        sharpness_score=81.0,
        lighting_score=39.0,
        resolution_score=68.0,
        face_quality_score=24.0,
    )

    assert explanation.confidence_label == "Unsicher"
    assert explanation.confidence_level == "low"
    assert explanation.concerns_text == "Schwaecher: Belichtung, Augen"
    assert "Mindestens ein wichtiges Bildmerkmal" in explanation.tooltip_text


def test_build_score_explanation_requests_reanalysis_for_legacy_score() -> None:
    explanation = build_score_explanation(
        quality_score=72.5,
        sharpness_score=None,
        lighting_score=None,
        resolution_score=None,
        face_quality_score=None,
    )

    assert explanation.has_any_data is True
    assert explanation.needs_reanalysis is True
    assert explanation.confidence_label == "Neu analysieren"
    assert explanation.component_details == ()
    assert "Details fehlen" in explanation.tooltip_text