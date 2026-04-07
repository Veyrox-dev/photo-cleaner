from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExplainedMetric:
    key: str
    label: str
    value: float


@dataclass(frozen=True)
class ScoreExplanation:
    has_any_data: bool
    overall_text: Optional[str]
    component_details: tuple[ExplainedMetric, ...]
    component_summary_text: Optional[str]
    strengths_text: Optional[str]
    concerns_text: Optional[str]
    confidence_label: Optional[str]
    confidence_reason: Optional[str]
    confidence_level: Optional[str]
    needs_reanalysis: bool
    tooltip_text: str


def build_score_explanation(
    *,
    quality_score: Optional[float],
    sharpness_score: Optional[float],
    lighting_score: Optional[float],
    resolution_score: Optional[float],
    face_quality_score: Optional[float],
) -> ScoreExplanation:
    metrics = _collect_metrics(
        sharpness_score=sharpness_score,
        lighting_score=lighting_score,
        resolution_score=resolution_score,
        face_quality_score=face_quality_score,
    )

    has_any_data = quality_score is not None or bool(metrics)
    if not has_any_data:
        return ScoreExplanation(
            has_any_data=False,
            overall_text=None,
            component_details=(),
            component_summary_text=None,
            strengths_text=None,
            concerns_text=None,
            confidence_label=None,
            confidence_reason=None,
            confidence_level=None,
            needs_reanalysis=False,
            tooltip_text="Keine Qualitaetsdaten verfuegbar",
        )

    overall_text = f"Gesamtscore: {quality_score:.1f}%" if quality_score is not None else None
    needs_reanalysis = quality_score is not None and not metrics

    strengths = [metric.label for metric in metrics if metric.value >= 75.0]
    concerns = [metric.label for metric in metrics if metric.value < 45.0]

    component_summary_text = _build_component_summary(metrics)
    strengths_text = f"Staerken: {', '.join(strengths)}" if strengths else None
    concerns_text = f"Bitte pruefen: {', '.join(concerns)}" if concerns else None
    confidence_label, confidence_reason, confidence_level = _classify_confidence(
        quality_score=quality_score,
        metrics=metrics,
        needs_reanalysis=needs_reanalysis,
        concerns=concerns,
    )
    tooltip_text = _build_tooltip(
        overall_text=overall_text,
        component_summary_text=component_summary_text,
        strengths_text=strengths_text,
        concerns_text=concerns_text,
        confidence_label=confidence_label,
        confidence_reason=confidence_reason,
        needs_reanalysis=needs_reanalysis,
    )

    return ScoreExplanation(
        has_any_data=True,
        overall_text=overall_text,
        component_details=tuple(metrics),
        component_summary_text=component_summary_text,
        strengths_text=strengths_text,
        concerns_text=concerns_text,
        confidence_label=confidence_label,
        confidence_reason=confidence_reason,
        confidence_level=confidence_level,
        needs_reanalysis=needs_reanalysis,
        tooltip_text=tooltip_text,
    )


def _collect_metrics(
    *,
    sharpness_score: Optional[float],
    lighting_score: Optional[float],
    resolution_score: Optional[float],
    face_quality_score: Optional[float],
) -> list[ExplainedMetric]:
    ordered_metrics = [
        ("sharpness", "Schaerfe", sharpness_score),
        ("lighting", "Belichtung", lighting_score),
        ("resolution", "Aufloesung", resolution_score),
        ("eyes", "Augen", face_quality_score),
    ]
    return [
        ExplainedMetric(key=key, label=label, value=float(value))
        for key, label, value in ordered_metrics
        if value is not None
    ]


def _build_component_summary(metrics: list[ExplainedMetric]) -> Optional[str]:
    if not metrics:
        return None

    ranked = sorted(metrics, key=lambda metric: metric.value, reverse=True)
    strongest = ranked[0]
    weakest = ranked[-1]

    if strongest.key == weakest.key:
        return f"Treiber: {strongest.label} {strongest.value:.0f}%"

    return (
        f"Treiber: {strongest.label} {strongest.value:.0f}% | "
        f"Schwaechste Stelle: {weakest.label} {weakest.value:.0f}%"
    )


def _classify_confidence(
    *,
    quality_score: Optional[float],
    metrics: list[ExplainedMetric],
    needs_reanalysis: bool,
    concerns: list[str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if needs_reanalysis:
        return (
            "Neu analysieren",
            "Es liegt nur ein Gesamtscore ohne Komponenten vor.",
            "incomplete",
        )

    if not metrics:
        return (None, None, None)

    min_value = min(metric.value for metric in metrics)
    avg_value = sum(metric.value for metric in metrics) / len(metrics)

    if quality_score is not None and quality_score >= 75.0 and min_value >= 60.0 and not concerns:
        return (
            "Hohe Sicherheit",
            "Alle Kernsignale liegen stabil im guten Bereich.",
            "high",
        )

    if len(concerns) >= 2 or min_value < 30.0 or (quality_score is not None and quality_score < 45.0):
        return (
            "Bitte pruefen",
            "Mindestens ein relevantes Signal ist deutlich schwach.",
            "low",
        )

    if avg_value >= 60.0:
        return (
            "Kurz pruefen",
            "Die Signale sind brauchbar, aber nicht durchgaengig stark.",
            "medium",
        )

    return (
        "Bitte pruefen",
        "Die Signale sind gemischt und brauchen eine manuelle Sichtpruefung.",
        "low",
    )


def _build_tooltip(
    *,
    overall_text: Optional[str],
    component_summary_text: Optional[str],
    strengths_text: Optional[str],
    concerns_text: Optional[str],
    confidence_label: Optional[str],
    confidence_reason: Optional[str],
    needs_reanalysis: bool,
) -> str:
    lines = []
    if overall_text:
        lines.append(overall_text)
    if confidence_label:
        confidence_line = confidence_label
        if confidence_reason:
            confidence_line = f"{confidence_line}: {confidence_reason}"
        lines.append(confidence_line)
    if component_summary_text:
        lines.append(component_summary_text)
    if strengths_text:
        lines.append(strengths_text)
    if concerns_text:
        lines.append(concerns_text)
    if needs_reanalysis:
        lines.append("Details fehlen: Analyse erneut ausfuehren, um die Komponenten anzuzeigen.")
    return "\n".join(lines)