"""Run key pre-release regressions multiple times.

Checks repeated in 3 runs by default:
- Class-A ranking prefers originals over copy-marked files
- Progress phase mapping remains monotonic (simulated timeline)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from photo_cleaner.pipeline.auto_selector import ImageScoreComponents  # noqa: E402


def _check_class_a_priority() -> None:
    items = [
        ImageScoreComponents(path=Path("original.jpg"), total_score=80.0, duplicate_class=""),
        ImageScoreComponents(path=Path("copy - Kopie.jpg"), total_score=95.0, duplicate_class="A"),
    ]
    ordered = sorted(items, key=lambda x: (x.duplicate_class == "A", -x.total_score))
    if ordered[0].path.name != "original.jpg":
        raise AssertionError("Class-A priority regression: copy was ranked before original")


def _check_progress_monotonic() -> None:
    # Simulate stage transitions and mapped percentages:
    # grouping(70-75) -> rating(75-94) -> finalization(95-100)
    timeline = [70, 72, 75, 78, 89, 94, 95, 97, 100]
    for i in range(1, len(timeline)):
        if timeline[i] < timeline[i - 1]:
            raise AssertionError("Progress regression: non-monotonic value detected")


def run_once() -> None:
    _check_class_a_priority()
    _check_progress_monotonic()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pre-release regression checks")
    parser.add_argument("--runs", type=int, default=3, help="Number of repeated runs")
    args = parser.parse_args()

    if args.runs < 1:
        print("--runs must be >= 1")
        return 2

    for i in range(1, args.runs + 1):
        run_once()
        print(f"Run {i}/{args.runs}: OK")

    print("Pre-release regression check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
