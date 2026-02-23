from __future__ import annotations

import sqlite3
from typing import Optional


class HistoryRepository:
    """Undo stack stored in status_history."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def last_action_id(self) -> Optional[str]:
        cur = self.conn.execute("SELECT action_id FROM status_history ORDER BY history_id DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else None

    def undo_last_action(self) -> bool:
        action_id = self.last_action_id()
        if not action_id:
            return False
        cur = self.conn.execute(
            """
            SELECT file_id, old_status, old_locked, old_decided_at
            FROM status_history
            WHERE action_id = ?
            ORDER BY history_id DESC
            """,
            (action_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return False
        for file_id, old_status, old_locked, old_decided_at in rows:
            self.conn.execute(
                "UPDATE files SET file_status = ?, is_locked = ?, decided_at = ? WHERE file_id = ?",
                (old_status, int(old_locked), old_decided_at, file_id),
            )
        self.conn.execute("DELETE FROM status_history WHERE action_id = ?", (action_id,))
        self.conn.commit()
        return True
