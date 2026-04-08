from pathlib import Path

from photo_cleaner.pipeline.scorer import GroupScorer


class _DummyResult:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.error = None


def _make_scores(n: int):
    return [
        (Path(f"img_{idx:02d}.jpg"), float(100 - idx), False)
        for idx in range(n)
    ]


def test_dynamic_topn_small_group_keeps_one(monkeypatch) -> None:
    scorer = GroupScorer(top_n=10)
    results = [_DummyResult(Path(f"img_{idx:02d}.jpg")) for idx in range(3)]
    monkeypatch.setattr(scorer, "auto_select_best_image", lambda _g, _r: (None, None, _make_scores(3)))

    score = scorer.score_group("G1", results)

    assert score.top_n == 1
    assert score.num_keep == 1


def test_dynamic_topn_medium_group_keeps_two(monkeypatch) -> None:
    scorer = GroupScorer(top_n=10)
    results = [_DummyResult(Path(f"img_{idx:02d}.jpg")) for idx in range(6)]
    monkeypatch.setattr(scorer, "auto_select_best_image", lambda _g, _r: (None, None, _make_scores(6)))

    score = scorer.score_group("G2", results)

    assert score.top_n == 2
    assert score.num_keep == 2


def test_dynamic_topn_large_group_keeps_three(monkeypatch) -> None:
    scorer = GroupScorer(top_n=10)
    results = [_DummyResult(Path(f"img_{idx:02d}.jpg")) for idx in range(12)]
    monkeypatch.setattr(scorer, "auto_select_best_image", lambda _g, _r: (None, None, _make_scores(12)))

    score = scorer.score_group("G3", results)

    assert score.top_n == 3
    assert score.num_keep == 3
