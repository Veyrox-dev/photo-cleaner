from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class _GroupLike(Protocol):
    group_id: str
    sample_path: object
    open_count: int
    needs_review_count: int
    confidence_level: str
    total: int


@dataclass(frozen=True)
class GroupFilterOptions:
    needs_review_only: bool = False
    open_only: bool = False
    low_confidence_only: bool = False
    high_impact_only: bool = False
    high_impact_threshold: int = 5


def group_matches_filters(group: _GroupLike, term: str, options: GroupFilterOptions) -> bool:
    """Return True when group should remain visible under current filter options."""
    normalized_term = term.strip().lower()

    if normalized_term:
        sample_path = str(group.sample_path).lower()
        if normalized_term not in group.group_id.lower() and normalized_term not in sample_path:
            return False

    if options.needs_review_only and group.needs_review_count <= 0:
        return False

    if options.open_only and group.open_count <= 0:
        return False

    if options.low_confidence_only and group.confidence_level not in {"low", "none"}:
        return False

    if options.high_impact_only and group.total < options.high_impact_threshold:
        return False

    return True
