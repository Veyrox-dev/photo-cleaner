"""Integration tests for startup migration coupling in run_ui.py."""

import logging
import sqlite3
import tempfile
from pathlib import Path

from run_ui import _apply_startup_migrations


def _table_exists(db_path: Path, table_name: str) -> bool:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def test_startup_migrates_legacy_db_to_v005() -> None:
    logger = logging.getLogger("test_startup_migrations")
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "legacy.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE files (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                file_status TEXT NOT NULL DEFAULT 'UNDECIDED'
            )
            """
        )
        conn.commit()
        conn.close()

        _apply_startup_migrations(db_path, logger)

        assert _table_exists(db_path, "geo_groups")
        assert _table_exists(db_path, "geo_group_images")
        assert _table_exists(db_path, "geocoding_cache")
        assert _table_exists(db_path, "grouping_fallback_log")

        conn = sqlite3.connect(str(db_path))
        versions = {row[0] for row in conn.execute("SELECT version FROM migrations").fetchall()}
        conn.close()
        assert "005" in versions


def test_startup_migration_is_idempotent() -> None:
    logger = logging.getLogger("test_startup_migrations")
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "idempotent.db"

        applied_first, _ = _apply_startup_migrations(db_path, logger)
        applied_second, _ = _apply_startup_migrations(db_path, logger)

        assert applied_first >= 1
        assert applied_second == 0

        conn = sqlite3.connect(str(db_path))
        versions = {row[0] for row in conn.execute("SELECT version FROM migrations").fetchall()}
        conn.close()
        assert "005" in versions