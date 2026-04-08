from __future__ import annotations

from typing import Optional


_METRIC_LABELS = {
    "sharpness": "Schaerfe",
    "lighting": "Belichtung",
    "resolution": "Aufloesung",
    "face": "Augen",
}


def compute_file_confidence_bucket(
    *,
    quality_score: Optional[float],
    sharpness_score: Optional[float],
    lighting_score: Optional[float],
    resolution_score: Optional[float],
    face_quality_score: Optional[float],
) -> int:
    """Return deterministic confidence bucket for one file.

    Buckets:
    - 100: high
    - 65: medium
    - 25: low
    - 10: incomplete legacy score
    - 0: no analysis data
    """
    metrics = [
        float(v)
        for v in (sharpness_score, lighting_score, resolution_score, face_quality_score)
        if v is not None
    ]

    if quality_score is None and not metrics:
        return 0

    if quality_score is not None and not metrics:
        return 10

    if not metrics:
        return 0

    min_value = min(metrics)
    avg_value = sum(metrics) / len(metrics)
    concern_count = sum(1 for value in metrics if value < 45.0)

    if quality_score is not None and quality_score >= 75.0 and min_value >= 60.0 and concern_count == 0:
        return 100

    if concern_count >= 2 or min_value < 30.0 or (quality_score is not None and quality_score < 45.0):
        return 25

    if avg_value >= 60.0:
        return 65

    return 25


def classify_group_confidence(bucket: int) -> str:
    if bucket >= 85:
        return "high"
    if bucket >= 50:
        return "medium"
    if bucket > 10:
        return "low"
    if bucket > 0:
        return "incomplete"
    return "none"


def build_group_diagnostics(
    *,
    weak_sharpness: int,
    weak_lighting: int,
    weak_resolution: int,
    weak_face: int,
    strong_sharpness: int,
    strong_lighting: int,
    strong_resolution: int,
    strong_face: int,
) -> str:
    weak_map = {
        "sharpness": int(weak_sharpness),
        "lighting": int(weak_lighting),
        "resolution": int(weak_resolution),
        "face": int(weak_face),
    }
    strong_map = {
        "sharpness": int(strong_sharpness),
        "lighting": int(strong_lighting),
        "resolution": int(strong_resolution),
        "face": int(strong_face),
    }

    weak_key, weak_count = max(weak_map.items(), key=lambda item: item[1])
    strong_key, strong_count = max(strong_map.items(), key=lambda item: item[1])

    if weak_count <= 0 and strong_count <= 0:
        return "Diagnose: keine Komponenten-Daten"

    if weak_count <= 0:
        return f"Treiber-Muster: {_METRIC_LABELS[strong_key]} ({strong_count})"

    if strong_count <= 0:
        return f"Schwachstellen-Muster: {_METRIC_LABELS[weak_key]} ({weak_count})"

    return (
        f"Treiber-Muster: {_METRIC_LABELS[strong_key]} ({strong_count}) | "
        f"Schwachstellen-Muster: {_METRIC_LABELS[weak_key]} ({weak_count})"
    )
