from __future__ import annotations

import sqlite3
from pathlib import Path

from photo_cleaner.exporter import Exporter, StreamingExporter
from photo_cleaner.repositories.file_repository import FileRepository


def _seed_files_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE files (
            file_id INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            is_locked INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            deleted_at INTEGER
        )
        """
    )
    conn.commit()


def test_export_and_mark_deleted_integration(tmp_path: Path) -> None:
    # Prepare real source files for export.
    src_1 = tmp_path / "a.jpg"
    src_2 = tmp_path / "b.jpg"
    src_1.write_bytes(b"img-a")
    src_2.write_bytes(b"img-b")

    out_dir = tmp_path / "out"
    exporter = Exporter(out_dir)
    success_count, failure_count, errors = exporter.export_files([src_1, src_2])

    assert success_count == 2
    assert failure_count == 0
    assert errors == []

    # Integration with delete path: one locked file must be skipped.
    conn = sqlite3.connect(":memory:")
    _seed_files_table(conn)
    conn.execute(
        "INSERT INTO files (file_id, path, is_locked, is_deleted) VALUES (1, ?, 0, 0)",
        (str(src_1),),
    )
    conn.execute(
        "INSERT INTO files (file_id, path, is_locked, is_deleted) VALUES (2, ?, 1, 0)",
        (str(src_2),),
    )
    conn.commit()

    repo = FileRepository(conn)
    result = repo.mark_deleted([1, 2])

    assert result["deleted_ids"] == [1]
    assert result["skipped_locked_ids"] == [2]

    rows = conn.execute("SELECT file_id, is_deleted FROM files ORDER BY file_id").fetchall()
    assert rows == [(1, 1), (2, 0)]


def test_streaming_export_partial_failure_integration(tmp_path: Path) -> None:
    good = tmp_path / "good.jpg"
    missing = tmp_path / "missing.jpg"
    good.write_bytes(b"ok")

    out_dir = tmp_path / "out"
    exporter = StreamingExporter(out_dir, archive_name="export.zip")

    success, failure, errors, archive_path, cancelled = exporter.export_files_streaming([good, missing])

    assert cancelled is False
    assert success == 1
    assert failure == 1
    assert len(errors) == 1
    assert archive_path.exists()
