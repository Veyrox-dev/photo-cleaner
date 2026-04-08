from __future__ import annotations

import sqlite3
from typing import Optional


_GROUP_REASSIGN_REASON_PREFIX = "GROUP_REASSIGN|"
_GROUP_SINGLE_SENTINEL = "__SINGLE__"


class HistoryRepository:
    """Undo stack stored in status_history."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def last_action_id(self) -> Optional[str]:
        cur = self.conn.execute("SELECT action_id FROM status_history ORDER BY history_id DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else None

    def describe_action(self, action_id: str) -> Optional[dict]:
        cur = self.conn.execute(
            """
            SELECT file_id, old_status, new_status, old_locked, new_locked, reason
            FROM status_history
            WHERE action_id = ?
            ORDER BY history_id DESC
            """,
            (action_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return None

        count = len(rows)
        group_reasons = [
            str(reason) for _file_id, _old_status, _new_status, _old_locked, _new_locked, reason in rows
            if reason and str(reason).startswith(_GROUP_REASSIGN_REASON_PREFIX)
        ]
        if group_reasons:
            source = "reassign"
            payload = group_reasons[0][len(_GROUP_REASSIGN_REASON_PREFIX):]
            for chunk in payload.split(";"):
                if chunk.startswith("source="):
                    source = chunk.split("=", 1)[1].strip()
                    break
            kind = {
                "merge": "group_merge",
                "split": "group_split",
            }.get(source, "group_reassign")
            return {"action_id": action_id, "kind": kind, "count": count}

        old_statuses = {str(old_status) for _file_id, old_status, _new_status, _old_locked, _new_locked, _reason in rows}
        new_statuses = {str(new_status) for _file_id, _old_status, new_status, _old_locked, _new_locked, _reason in rows}
        old_locked = {int(old_locked) for _file_id, _old_status, _new_status, old_locked, _new_locked, _reason in rows}
        new_locked = {int(new_locked) for _file_id, _old_status, _new_status, _old_locked, new_locked, _reason in rows}

        if old_statuses == new_statuses and old_locked != new_locked:
            return {
                "action_id": action_id,
                "kind": "lock_toggle",
                "count": count,
                "locked": 1 in new_locked,
            }

        new_status = next(iter(new_statuses), None)
        return {
            "action_id": action_id,
            "kind": "status_change",
            "count": count,
            "new_status": new_status,
        }

    def describe_last_action(self) -> Optional[dict]:
        action_id = self.last_action_id()
        if not action_id:
            return None
        return self.describe_action(action_id)

    def recent_actions(self, limit: int = 5) -> list[dict]:
        cur = self.conn.execute(
            """
            SELECT action_id
            FROM status_history
            GROUP BY action_id
            ORDER BY MAX(history_id) DESC
            LIMIT ?
            """,
            (limit,),
        )
        action_ids = [str(row[0]) for row in cur.fetchall()]
        actions: list[dict] = []
        for action_id in action_ids:
            description = self.describe_action(action_id)
            if description:
                actions.append(description)
        return actions

    def record_group_reassignment(
        self,
        *,
        action_id: str,
        file_id: int,
        old_group_id: Optional[str],
        new_group_id: str,
        reason: str = "",
    ) -> None:
        """Store merge/split reassignment in status_history so undo can restore groups.

        We persist reassignment metadata in `reason` while keeping status fields unchanged.
        """
        cur = self.conn.execute(
            "SELECT path, file_status, is_locked, decided_at FROM files WHERE file_id = ?",
            (file_id,),
        )
        row = cur.fetchone()
        if not row:
            raise KeyError(f"File not found for history record: {file_id}")

        file_path, status, is_locked, decided_at = row
        old_group_token = old_group_id if old_group_id is not None else _GROUP_SINGLE_SENTINEL
        full_reason = (
            f"{_GROUP_REASSIGN_REASON_PREFIX}old={old_group_token};new={new_group_id};{reason}"
            if reason
            else f"{_GROUP_REASSIGN_REASON_PREFIX}old={old_group_token};new={new_group_id}"
        )
        self.conn.execute(
            """
            INSERT INTO status_history (action_id, file_id, file_path, old_status, new_status, old_locked, new_locked, old_decided_at, new_decided_at, reason)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                action_id,
                file_id,
                file_path,
                status,
                status,
                int(is_locked),
                int(is_locked),
                decided_at,
                decided_at,
                full_reason,
            ),
        )

    def _undo_group_reassignment(self, rows) -> bool:
        for file_id, _old_status, _old_locked, _old_decided_at, reason in rows:
            if not reason or not str(reason).startswith(_GROUP_REASSIGN_REASON_PREFIX):
                continue

            payload = str(reason)[len(_GROUP_REASSIGN_REASON_PREFIX):]
            parts = {}
            for chunk in payload.split(";"):
                if "=" in chunk:
                    key, value = chunk.split("=", 1)
                    parts[key.strip()] = value.strip()

            old_group_token = parts.get("old", "")
            if old_group_token == _GROUP_SINGLE_SENTINEL:
                self.conn.execute("DELETE FROM duplicates WHERE file_id = ?", (file_id,))
                continue

            existing = self.conn.execute(
                "SELECT duplicate_id FROM duplicates WHERE file_id = ? LIMIT 1",
                (file_id,),
            ).fetchone()
            if existing:
                self.conn.execute(
                    "UPDATE duplicates SET group_id = ? WHERE file_id = ?",
                    (old_group_token, file_id),
                )
            else:
                self.conn.execute(
                    "INSERT INTO duplicates (group_id, file_id, similarity_score, is_keeper) VALUES (?, ?, ?, 0)",
                    (old_group_token, file_id, 1.0),
                )
        return True

    def undo_last_action(self) -> bool:
        action_id = self.last_action_id()
        if not action_id:
            return False
        cur = self.conn.execute(
            """
            SELECT file_id, old_status, old_locked, old_decided_at, reason
            FROM status_history
            WHERE action_id = ?
            ORDER BY history_id DESC
            """,
            (action_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return False
        is_group_reassign = any(
            reason and str(reason).startswith(_GROUP_REASSIGN_REASON_PREFIX)
            for _file_id, _old_status, _old_locked, _old_decided_at, reason in rows
        )

        if is_group_reassign:
            self._undo_group_reassignment(rows)
        else:
            for file_id, old_status, old_locked, old_decided_at, _reason in rows:
                self.conn.execute(
                    "UPDATE files SET file_status = ?, is_locked = ?, decided_at = ? WHERE file_id = ?",
                    (old_status, int(old_locked), old_decided_at, file_id),
                )
        self.conn.execute("DELETE FROM status_history WHERE action_id = ?", (action_id,))
        self.conn.commit()
        return True
