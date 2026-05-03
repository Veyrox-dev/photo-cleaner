"""E2E and performance validation for the watch-folder autoimport pipeline."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from unittest.mock import Mock

from PIL import Image

from photo_cleaner.autoimport.autoimport_pipeline import AutoimportPipeline


def _create_image(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (64, 64), color=color).save(path, format="JPEG")


def test_autoimport_pipeline_indexes_and_groups_duplicates(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "autoimport_e2e.db"
    config_mock = Mock()
    license_mock = Mock()
    pipeline = AutoimportPipeline(db_path, config_mock, license_mock)

    image_a = tmp_path / "a.jpg"
    image_b = tmp_path / "b.jpg"
    image_c = tmp_path / "c.jpg"
    _create_image(image_a, (200, 50, 50))
    image_b.write_bytes(image_a.read_bytes())
    _create_image(image_c, (50, 120, 200))

    def fake_run(self):
        self.finished.emit({"rated": True, "warn": False})

    monkeypatch.setattr(
        "photo_cleaner.autoimport.autoimport_pipeline.RatingWorkerThread.run",
        fake_run,
    )

    results: list[dict] = []
    pipeline.import_completed.connect(results.append)

    pipeline.analyze_files([str(image_a), str(image_b), str(image_c)])

    assert len(results) == 1
    assert results[0]["total_files"] == 3
    assert results[0]["indexed_files"] == 3
    assert results[0]["duplicates_found"] >= 1
    assert results[0]["rating"]["rated"] is True

    with sqlite3.connect(db_path) as con:
        file_count = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        duplicate_groups = con.execute("SELECT COUNT(DISTINCT group_id) FROM duplicates").fetchone()[0]

    assert file_count == 3
    assert duplicate_groups >= 1


def test_autoimport_pipeline_batch_finishes_under_five_seconds(monkeypatch, tmp_path) -> None:
    """Indicative performance guard for a small watch-folder batch."""
    db_path = tmp_path / "autoimport_perf.db"
    config_mock = Mock()
    license_mock = Mock()
    pipeline = AutoimportPipeline(db_path, config_mock, license_mock)

    image_paths: list[Path] = []
    for index in range(12):
        image_path = tmp_path / f"perf_{index:02d}.jpg"
        _create_image(image_path, ((index % 3) * 40 + 20, 80, 120))
        if index % 4 == 1:
            image_path.write_bytes(image_paths[-1].read_bytes())
        image_paths.append(image_path)

    def fake_run(self):
        self.finished.emit({"rated": True, "warn": False})

    monkeypatch.setattr(
        "photo_cleaner.autoimport.autoimport_pipeline.RatingWorkerThread.run",
        fake_run,
    )

    start = time.perf_counter()
    pipeline.analyze_files([str(path) for path in image_paths])
    elapsed = time.perf_counter() - start

    with sqlite3.connect(db_path) as con:
        file_count = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    assert elapsed < 5.0
    assert file_count == 12
