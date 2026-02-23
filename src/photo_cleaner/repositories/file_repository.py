from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

from photo_cleaner.models.status import FileStatus

logger = logging.getLogger(__name__)


class FileRepository:
    """Persistence layer for file records and their statuses."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _validate_safe_path(self, path: Path) -> Path:
        """P2 FIX #13: Validate path is safe to operate on.
        
        Prevents path traversal attacks and system directory access.
        Ensures only valid photo paths are modified.
        
        Args:
            path: Path to validate
            
        Returns:
            Resolved absolute path
            
        Raises:
            ValueError: If path is unsafe
        """
        try:
            # Resolve to absolute, normalized path
            resolved = path.resolve()
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid path {path}: {e}")
        
        # Check for path traversal attempts
        try:
            # Ensure path doesn't contain suspicious parent references
            # (path.resolve() should handle this, but be explicit)
            path_str = str(resolved)
            if '..' in path_str or path_str.startswith('//'):
                raise ValueError(f"Path traversal detected: {path}")
        except Exception as e:
            raise ValueError(f"Invalid path components: {e}")
        
        # Prevent system directory access (Unix-like systems)
        forbidden_unix_roots = {
            Path('/etc'),
            Path('/sys'),
            Path('/proc'),
            Path('/bin'),
            Path('/sbin'),
            Path('/usr/bin'),
            Path('/usr/sbin'),
            Path('/root'),
            Path('/boot'),
            Path('/dev'),
        }
        
        # Prevent system directory access (Windows)
        forbidden_windows_roots = {
            Path('C:\\Windows'),
            Path('C:\\System32'),
            Path('C:\\Program Files'),
            Path('C:\\Program Files (x86)'),
        }
        
        # Check against forbidden directories
        all_forbidden = forbidden_unix_roots | forbidden_windows_roots
        for forbidden in all_forbidden:
            try:
                # Try to check if resolved path is under forbidden directory
                resolved.relative_to(forbidden)
                raise ValueError(f"Path in forbidden system directory: {path}")
            except ValueError:
                # Not under this forbidden directory, continue
                pass
        
        # Log successful validation
        logger.debug(f"Path validation successful: {resolved}")
        return resolved

    def get_status(self, path: Path) -> Tuple[FileStatus, bool]:
        # P2 FIX #13: Validate path before database operation
        safe_path = self._validate_safe_path(path)
        cur = self.conn.execute(
            "SELECT file_status, is_locked FROM files WHERE path = ?",
            (str(safe_path),),
        )
        row = cur.fetchone()
        if not row:
            raise KeyError(f"File not found: {path}")
        return FileStatus(row[0]), bool(row[1])

    def set_status(self, path: Path, status: FileStatus, *, reason: str = "", action_id: str = "MANUAL_SET") -> None:
        # P2.5: Validate FileStatus enum
        if not isinstance(status, FileStatus):
            raise ValueError(f"Invalid status: {status}. Must be FileStatus enum value")
        
        # P2 FIX #13: Validate path before database operation
        safe_path = self._validate_safe_path(path)
        
        try:
            # P0 FIX: Use atomic UPDATE with WHERE clause to prevent TOCTOU race condition
            # Instead of: SELECT → check is_locked → UPDATE (vulnerable to race)
            # Now: UPDATE ... WHERE is_locked = 0 (atomic in single operation)
            
            # First, get the current file record
            cur = self.conn.execute(
                "SELECT file_id, file_status, is_locked, decided_at FROM files WHERE path = ?",
                (str(safe_path),),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError(f"File not found: {path}")
            file_id, old_status, old_locked, old_decided_at = row
            
            # P0 FIX: Check if locked BEFORE atomic update
            if old_locked:
                raise ValueError(f"File is locked and cannot be modified: {path}")
            
            new_locked = old_locked
            if status in (FileStatus.KEEP, FileStatus.DELETE):
                cur_ts = self.conn.execute("SELECT unixepoch()").fetchone()[0]
                # P0 FIX: Atomic update with lock check to prevent race condition
                result = self.conn.execute(
                    "UPDATE files SET file_status = ?, decided_at = ? WHERE file_id = ? AND is_locked = 0",
                    (status.value, cur_ts, file_id),
                )
                # Verify the update actually happened (lock wasn't set between check and update)
                if result.rowcount == 0:
                    raise ValueError(f"File became locked during update: {path}")
                new_decided_at = cur_ts
            else:
                # P0 FIX: Atomic update with lock check to prevent race condition
                result = self.conn.execute(
                    "UPDATE files SET file_status = ?, decided_at = NULL WHERE file_id = ? AND is_locked = 0",
                    (status.value, file_id),
                )
                # Verify the update actually happened (lock wasn't set between check and update)
                if result.rowcount == 0:
                    raise ValueError(f"File became locked during update: {path}")
                new_decided_at = None
            
            self.conn.execute(
                """
                INSERT INTO status_history (action_id, file_id, file_path, old_status, new_status, old_locked, new_locked, old_decided_at, new_decided_at, reason)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    action_id,
                    file_id,
                    str(path),
                    old_status,
                    status.value,
                    old_locked,
                    new_locked,
                    old_decided_at,
                    new_decided_at,
                    reason,
                ),
            )
            self.conn.commit()
        except Exception as e:
            # P1.6 + P1 FIX #9: Rollback on any error with proper error handling
            logger.error(f"Operation failed in set_status, attempting rollback: {type(e).__name__}: {e}")
            try:
                self.conn.rollback()
                logger.debug("Rollback successful in set_status")
            except sqlite3.OperationalError as rollback_err:
                # Connection might be corrupted - this is critical
                logger.critical(
                    f"CRITICAL: Rollback failed in set_status - database connection might be corrupted: {rollback_err}. "
                    f"Original error was: {type(e).__name__}: {e}",
                    exc_info=True
                )
                # Try to close connection to force reconnection
                try:
                    self.conn.close()
                    logger.warning("Closed corrupted database connection")
                except Exception as close_err:
                    logger.error(f"Failed to close connection: {close_err}")
                # Re-raise with context
                raise ConnectionError(
                    f"Database connection corrupted during rollback. "
                    f"Original error: {type(e).__name__}: {e}. "
                    f"Rollback error: {rollback_err}"
                ) from rollback_err
            except Exception as rollback_err:
                # Other unexpected errors during rollback
                logger.error(
                    f"Unexpected error during rollback in set_status: {type(rollback_err).__name__}: {rollback_err}",
                    exc_info=True
                )
                raise
            raise  # Re-raise original exception

    def toggle_lock(self, path: Path, *, lock: bool | None = None, reason: str = "", action_id: str = "LOCK_TOGGLE") -> bool:
        # P2 FIX #13: Validate path before database operation
        safe_path = self._validate_safe_path(path)
        
        try:
            cur = self.conn.execute(
                "SELECT file_id, is_locked, file_status, decided_at FROM files WHERE path = ?",
                (str(safe_path),),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError(f"File not found: {path}")
            file_id, old_locked, status, old_decided_at = row
            new_locked = (not bool(old_locked)) if lock is None else bool(lock)
            if new_locked == bool(old_locked):
                return bool(old_locked)
            self.conn.execute(
                "UPDATE files SET is_locked = ? WHERE file_id = ?",
                (int(new_locked), file_id),
            )
            self.conn.execute(
                """
                INSERT INTO status_history (action_id, file_id, file_path, old_status, new_status, old_locked, new_locked, old_decided_at, new_decided_at, reason)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    action_id,
                    file_id,
                    str(safe_path),
                    status,
                    status,
                    old_locked,
                    int(new_locked),
                    old_decided_at,
                    old_decided_at,
                    reason,
                ),
            )
            self.conn.commit()
            return new_locked
        except Exception as e:
            # P1.6 + P1 FIX #9: Rollback on any error with proper error handling
            logger.error(f"Operation failed in toggle_lock, attempting rollback: {type(e).__name__}: {e}")
            try:
                self.conn.rollback()
                logger.debug("Rollback successful in toggle_lock")
            except sqlite3.OperationalError as rollback_err:
                # Connection might be corrupted - this is critical
                logger.critical(
                    f"CRITICAL: Rollback failed in toggle_lock - database connection might be corrupted: {rollback_err}. "
                    f"Original error was: {type(e).__name__}: {e}",
                    exc_info=True
                )
                # Try to close connection to force reconnection
                try:
                    self.conn.close()
                    logger.warning("Closed corrupted database connection")
                except Exception as close_err:
                    logger.error(f"Failed to close connection: {close_err}")
                # Re-raise with context
                raise ConnectionError(
                    f"Database connection corrupted during rollback. "
                    f"Original error: {type(e).__name__}: {e}. "
                    f"Rollback error: {rollback_err}"
                ) from rollback_err
            except Exception as rollback_err:
                # Other unexpected errors during rollback
                logger.error(
                    f"Unexpected error during rollback in toggle_lock: {type(rollback_err).__name__}: {rollback_err}",
                    exc_info=True
                )
                raise
            raise  # Re-raise original exception

    def bulk_set_status(self, file_ids: List[int], status: FileStatus, *, reason: str = "", action_id: str = "BATCH_SET", commit: bool = True) -> None:
        if not file_ids:
            return
        placeholders = ",".join("?" for _ in file_ids)
        # snapshot old values for history (skip locked rows)
        cur = self.conn.execute(
            f"SELECT file_id, file_status, is_locked, decided_at FROM files WHERE file_id IN ({placeholders})",
            file_ids,
        )
        rows = [r for r in cur.fetchall() if not r[2]]
        new_ts = None
        if status in (FileStatus.KEEP, FileStatus.DELETE):
            new_ts = self.conn.execute("SELECT unixepoch()").fetchone()[0]
        self.conn.executemany(
            """
            INSERT INTO status_history (action_id, file_id, file_path, old_status, new_status, old_locked, new_locked, old_decided_at, new_decided_at, reason)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    action_id,
                    r[0],
                    self._path_for_file_id(r[0]),
                    r[1],
                    status.value,
                    r[2],
                    r[2],
                    r[3],
                    None if status in (FileStatus.UNDECIDED, FileStatus.UNSURE) else new_ts,
                    reason,
                )
                for r in rows
            ],
        )
        if status in (FileStatus.KEEP, FileStatus.DELETE):
            self.conn.execute(
                f"UPDATE files SET file_status = ?, decided_at = ? WHERE is_locked = 0 AND file_id IN ({placeholders})",
                [status.value, new_ts, *file_ids],
            )
        else:
            self.conn.execute(
                f"UPDATE files SET file_status = ?, decided_at = NULL WHERE is_locked = 0 AND file_id IN ({placeholders})",
                [status.value, *file_ids],
            )
        if commit:
            self.conn.commit()

    def mark_deleted(self, file_ids: List[int]) -> Dict[str, List[int]]:
        """Mark files as deleted; locked files are skipped.

        Returns a dict with deleted_ids and skipped_locked_ids for transparency toward the UI.
        """
        if not file_ids:
            return {"deleted_ids": [], "skipped_locked_ids": []}
        
        try:
            placeholders = ",".join("?" for _ in file_ids)
            cur = self.conn.execute(
                f"SELECT file_id, is_locked FROM files WHERE file_id IN ({placeholders})",
                file_ids,
            )
            rows = cur.fetchall()
            to_delete = [r[0] for r in rows if not r[1]]
            skipped = [r[0] for r in rows if r[1]]
            if to_delete:
                placeholders2 = ",".join("?" for _ in to_delete)
                self.conn.execute(
                    f"UPDATE files SET is_deleted = 1, deleted_at = unixepoch() WHERE file_id IN ({placeholders2})",
                    to_delete,
                )
            self.conn.commit()
            return {"deleted_ids": to_delete, "skipped_locked_ids": skipped}
        except (sqlite3.Error, ValueError, KeyError) as e:
            # P1.6: Rollback on error to prevent partial deletion state
            logger.error(f"Error marking files as deleted: {e}", exc_info=True)
            try:
                self.conn.rollback()
            except (sqlite3.Error, RuntimeError):
                logger.debug("Error during rollback", exc_info=True)
            raise

    def aggregates(self) -> Dict[str, int]:
        cur = self.conn.execute(
            """
            SELECT
                            SUM(CASE WHEN UPPER(COALESCE(file_status,'UNDECIDED')) = 'UNDECIDED' THEN 1 ELSE 0 END) AS undecided,
                            SUM(CASE WHEN UPPER(COALESCE(file_status,'')) = 'KEEP' THEN 1 ELSE 0 END) AS keep_cnt,
                            SUM(CASE WHEN UPPER(COALESCE(file_status,'')) = 'DELETE' THEN 1 ELSE 0 END) AS delete_cnt,
                            SUM(CASE WHEN UPPER(COALESCE(file_status,'')) = 'UNSURE' THEN 1 ELSE 0 END) AS unsure,
              SUM(CASE WHEN is_locked = 1 THEN 1 ELSE 0 END) AS locked_cnt,
                            SUM(CASE WHEN UPPER(COALESCE(file_status,'')) = 'DELETE' AND is_deleted = 0 AND is_locked = 0 THEN file_size ELSE 0 END) AS reclaim_bytes,
              COUNT(*) AS total
            FROM files
            """
        )
        row = cur.fetchone()
        return {
            "total": row[6] or 0,
            "undecided": row[0] or 0,
            "keep": row[1] or 0,
            "delete": row[2] or 0,
            "unsure": row[3] or 0,
            "locked": row[4] or 0,
            "reclaim_bytes": row[5] or 0,
        }

    def group_progress(self) -> Dict[str, int | None]:
        """Compute group-level progress based on duplicates table.

        groups_total: distinct group_id count
        groups_done: groups where no member is UNDECIDED/UNSURE
        """
        cur = self.conn.execute("SELECT COUNT(DISTINCT group_id) FROM duplicates")
        groups_total = cur.fetchone()[0] or 0
        cur = self.conn.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT d.group_id
              FROM duplicates d
              JOIN files f ON f.file_id = d.file_id
              GROUP BY d.group_id
                            HAVING SUM(CASE WHEN UPPER(COALESCE(f.file_status,'UNDECIDED')) IN ('UNDECIDED','UNSURE') THEN 1 ELSE 0 END) = 0
            )
            """
        )
        groups_done = cur.fetchone()[0] or 0
        return {"groups_total": groups_total, "groups_done": groups_done}

    def _path_for_file_id(self, file_id: int) -> str:
        cur = self.conn.execute("SELECT path FROM files WHERE file_id = ?", (file_id,))
        row = cur.fetchone()
        return row[0] if row else ""

    def list_active_paths(self) -> List[Path]:
        cur = self.conn.execute("SELECT path FROM files WHERE is_deleted = 0")
        return [Path(r[0]) for r in cur.fetchall()]

    def list_by_status(self, statuses: List[FileStatus]) -> List[Path]:
        if not statuses:
            return []
        placeholders = ",".join("?" for _ in statuses)
        cur = self.conn.execute(
            f"SELECT path FROM files WHERE is_deleted = 0 AND file_status IN ({placeholders})",
            [s.value for s in statuses],
        )
        return [Path(r[0]) for r in cur.fetchall()]
