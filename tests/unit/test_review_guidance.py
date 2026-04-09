from __future__ import annotations

from dataclasses import dataclass

from photo_cleaner.ui.review_guidance import recommend_next_step


@dataclass
class _Group:
    open_count: int
    needs_review_count: int
    confidence_level: str
    total: int


def _t(key: str) -> str:
    return key


def test_recommend_next_step_done_for_closed_group() -> None:
    group = _Group(open_count=0, needs_review_count=0, confidence_level="high", total=2)

    assert recommend_next_step(group, _t) == "review_guidance_done"


def test_recommend_next_step_low_confidence_priority() -> None:
    group = _Group(open_count=2, needs_review_count=1, confidence_level="low", total=3)

    assert recommend_next_step(group, _t) == "review_guidance_low_confidence"


def test_recommend_next_step_large_group_hint() -> None:
    group = _Group(open_count=3, needs_review_count=0, confidence_level="medium", total=7)

    assert recommend_next_step(group, _t) == "review_guidance_large_open"


def test_recommend_next_step_continue_default() -> None:
    group = _Group(open_count=2, needs_review_count=0, confidence_level="high", total=3)

    assert recommend_next_step(group, _t) == "review_guidance_continue"
