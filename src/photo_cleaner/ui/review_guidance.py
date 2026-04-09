from __future__ import annotations

from typing import Callable, Protocol


class _GroupLike(Protocol):
    open_count: int
    needs_review_count: int
    confidence_level: str
    total: int


def recommend_next_step(group: _GroupLike, t_func: Callable[[str], str]) -> str:
    """Return a short, actionable review hint for the currently selected group."""
    if group.open_count <= 0:
        return t_func("review_guidance_done")

    if group.needs_review_count > 0 or group.confidence_level in {"low", "none"}:
        return t_func("review_guidance_low_confidence")

    if group.total >= 5:
        return t_func("review_guidance_large_open")

    return t_func("review_guidance_continue")
