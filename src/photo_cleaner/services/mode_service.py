from __future__ import annotations

import sqlite3
from photo_cleaner.models.mode import AppMode


class ModeService:
    """Stores and retrieves the global application mode in metadata."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_mode(self) -> AppMode:
        cur = self.conn.execute("SELECT value FROM metadata WHERE key = 'app_mode'")
        row = cur.fetchone()
        return AppMode(row[0]) if row else AppMode.SAFE_MODE

    def set_mode(self, mode: AppMode) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('app_mode', ?)",
            (mode.value,),
        )
        self.conn.commit()

    def get_capabilities(self) -> dict:
        mode = self.get_mode()
        if mode == AppMode.CLEANUP_MODE:
            return {
                "can_delete": True,
                "can_batch": True,
                "can_apply_rules": True,
                "shows_similar": True,
            }
        if mode == AppMode.REVIEW_MODE:
            return {
                "can_delete": False,
                "can_batch": False,
                "can_apply_rules": False,
                "shows_similar": True,
            }
        # SAFE_MODE default
        return {
            "can_delete": False,
            "can_batch": False,
            "can_apply_rules": False,
            "shows_similar": False,
        }
