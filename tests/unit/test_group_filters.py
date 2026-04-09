from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from photo_cleaner.ui.group_filters import GroupFilterOptions, group_matches_filters


@dataclass
class _Group:
    group_id: str
    sample_path: Path
    open_count: int
    needs_review_count: int
    confidence_level: str
    total: int


def test_term_filter_matches_group_id_or_path() -> None:
    group = _Group("G000123", Path("C:/photos/summer.jpg"), 1, 0, "high", 2)

    assert group_matches_filters(group, "123", GroupFilterOptions()) is True
    assert group_matches_filters(group, "summer", GroupFilterOptions()) is True
    assert group_matches_filters(group, "winter", GroupFilterOptions()) is False


def test_open_only_filters_closed_groups() -> None:
    open_group = _Group("G1", Path("a.jpg"), 1, 0, "high", 2)
    closed_group = _Group("G2", Path("b.jpg"), 0, 0, "high", 2)
    opts = GroupFilterOptions(open_only=True)

    assert group_matches_filters(open_group, "", opts) is True
    assert group_matches_filters(closed_group, "", opts) is False


def test_low_confidence_only_accepts_low_and_none() -> None:
    low_group = _Group("G1", Path("a.jpg"), 1, 0, "low", 2)
    none_group = _Group("G2", Path("b.jpg"), 1, 0, "none", 2)
    high_group = _Group("G3", Path("c.jpg"), 1, 0, "high", 2)
    opts = GroupFilterOptions(low_confidence_only=True)

    assert group_matches_filters(low_group, "", opts) is True
    assert group_matches_filters(none_group, "", opts) is True
    assert group_matches_filters(high_group, "", opts) is False


def test_high_impact_only_uses_threshold() -> None:
    small = _Group("G1", Path("a.jpg"), 1, 0, "high", 3)
    large = _Group("G2", Path("b.jpg"), 1, 0, "high", 8)
    opts = GroupFilterOptions(high_impact_only=True, high_impact_threshold=5)

    assert group_matches_filters(small, "", opts) is False
    assert group_matches_filters(large, "", opts) is True


def test_combined_filters_all_must_match() -> None:
    group = _Group("G5", Path("x.jpg"), 2, 1, "low", 7)
    opts = GroupFilterOptions(
        needs_review_only=True,
        open_only=True,
        low_confidence_only=True,
        high_impact_only=True,
        high_impact_threshold=5,
    )

    assert group_matches_filters(group, "G5", opts) is True
    assert group_matches_filters(group, "missing", opts) is False
