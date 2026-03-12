from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional

from photo_cleaner.models.mode import AppMode
from photo_cleaner.models.status import FileStatus
from photo_cleaner.repositories.file_repository import FileRepository
from photo_cleaner.repositories.history_repository import HistoryRepository
from photo_cleaner.services.mode_service import ModeService
from photo_cleaner.services.progress_service import ProgressService
from photo_cleaner.services.rule_simulator import RuleResult, RuleSimulator
from photo_cleaner.services.status_service import StatusService
from photo_cleaner.pipeline.camera_calibrator import CameraCalibrator
from photo_cleaner.cache.image_cache_manager import ImageCacheManager

logger = logging.getLogger(__name__)


# ---------- Response helpers ----------

def ok(**kwargs) -> dict:
    return {"ok": True, **kwargs}

def err(code: str, message: str) -> dict:
    return {"ok": False, "error": code, "message": message}


# ---------- Facade ----------

class UIActions:
    """UI-facing facade. Catches exceptions, never trusts UI, enforces service guards.

    Each method returns a structured dict with ok/error/message and optional payload.
    """

    def __init__(
        self,
        files: FileRepository,
        history: HistoryRepository,
        mode_svc: ModeService,
        progress_svc: ProgressService,
        rule_sim: RuleSimulator,
        status_svc: StatusService,
        camera_calibrator: Optional[CameraCalibrator] = None,
        cache_manager: Optional[ImageCacheManager] = None,
    ) -> None:
        self.files = files
        self.history = history
        self.mode_svc = mode_svc
        self.progress_svc = progress_svc
        self.rule_sim = rule_sim
        self.status_svc = status_svc
        self.camera_calibrator = camera_calibrator
        self.cache_manager = cache_manager

    # --- Status setters ---
    def ui_set_keep(self, path: Path) -> dict:
        try:
            # PHASE 4 FIX 1: Record decision for calibration insights
            if self.camera_calibrator and self.cache_manager:
                quality_result = self.cache_manager.get_cached_result(str(path))
                if quality_result and quality_result.get("camera_model") not in (None, "unknown"):
                    self.camera_calibrator.record_image_decision(
                        camera_model=quality_result["camera_model"],
                        sharpness_value=quality_result.get("overall_sharpness", 0.0),
                        was_kept=True
                    )
            
            self.status_svc.set_status(path, FileStatus.KEEP, action_id="MANUAL_SET_KEEP")
            return ok()
        except PermissionError as e:
            return err("PERMISSION_DENIED", str(e))
        except (KeyError, ValueError, TypeError) as e:
            return err("INVALID_DATA", f"Invalid cache result: {str(e)}")
        except OSError as e:
            return err("FILE_ERROR", str(e))
        except Exception as e:
            logger.error(f"Unexpected error in ui_set_keep: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    def ui_set_delete(self, path: Path, *, allow_delete_in_safe: bool = False) -> dict:
        try:
            # PHASE 4 FIX 1: Record decision for calibration insights
            if self.camera_calibrator and self.cache_manager:
                quality_result = self.cache_manager.get_cached_result(str(path))
                if quality_result and quality_result.get("camera_model") not in (None, "unknown"):
                    self.camera_calibrator.record_image_decision(
                        camera_model=quality_result["camera_model"],
                        sharpness_value=quality_result.get("overall_sharpness", 0.0),
                        was_kept=False
                    )
            
            self.status_svc.set_status(
                path,
                FileStatus.DELETE,
                allow_delete_in_safe=allow_delete_in_safe,
                action_id="MANUAL_SET_DELETE",
            )
            return ok()
        except PermissionError as e:
            msg = str(e)
            if "SAFE_MODE" in msg:
                return err("SAFE_MODE_BLOCKED", "Löschen im SAFE_MODE nur bei exakten Duplikaten erlaubt.")
            if "locked" in msg.lower():
                return err("FILE_LOCKED", "Datei ist gesperrt und kann nicht gelöscht werden.")
            return err("PERMISSION_DENIED", msg)
        except (KeyError, ValueError, TypeError) as e:
            return err("INVALID_DATA", f"Invalid cache result: {str(e)}")
        except OSError as e:
            return err("FILE_ERROR", str(e))
        except Exception as e:
            logger.error(f"Unexpected error in ui_set_delete: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    def ui_set_unsure(self, path: Path) -> dict:
        try:
            self.status_svc.set_status(path, FileStatus.UNSURE, action_id="MANUAL_SET_UNSURE")
            return ok()
        except (KeyError, ValueError) as e:
            return err("INVALID_PATH", str(e))
        except OSError as e:
            return err("FILE_ERROR", str(e))
        except Exception as e:
            logger.error(f"Unexpected error in ui_set_unsure: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    def ui_set_undecided(self, path: Path) -> dict:
        try:
            self.status_svc.set_status(path, FileStatus.UNDECIDED, action_id="MANUAL_SET_UNDECIDED")
            return ok()
        except (KeyError, ValueError) as e:
            return err("INVALID_PATH", str(e))
        except OSError as e:
            return err("FILE_ERROR", str(e))
        except Exception as e:
            logger.error(f"Unexpected error in ui_set_undecided: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    # --- Batch status update (ATOMIC - Critical for data integrity) ---
    def ui_batch_set_status(self, paths: List[Path], status: FileStatus) -> dict:
        """Set status for multiple paths atomically.
        
        CRITICAL: Uses explicit transaction with SAVEPOINT for rollback on partial failure.
        BUG #8 FIX: Proper error handling with transaction rollback.
        """
        if not paths:
            return ok(updated=0)
        
        try:
            # Start explicit transaction
            self.files.conn.execute("BEGIN IMMEDIATE")  # Acquire write lock immediately
            
            try:
                # Validate all files exist and are not locked
                placeholders = ",".join("?" for _ in paths)
                cur = self.files.conn.execute(
                    f"SELECT file_id, path, is_locked FROM files WHERE path IN ({placeholders})",
                    [str(p) for p in paths],
                )
                rows = cur.fetchall()
                if len(rows) != len(paths):
                    found = {r[1] for r in rows}
                    missing = [p.name for p in paths if str(p) not in found]
                    self.files.conn.rollback()
                    return err("FILE_NOT_FOUND", f"Missing files: {', '.join(missing)}")
                
                locked = [r for r in rows if r[2]]
                if locked:
                    self.files.conn.rollback()
                    return err("FILE_LOCKED", f"File {Path(locked[0][1]).name} is locked")
                
                file_ids = [r[0] for r in rows]
                if not file_ids:
                    self.files.conn.commit()
                    return ok(updated=0, total=len(paths))
                
                # Perform batch update in transaction
                self.files.bulk_set_status(file_ids, status, reason="", action_id="BATCH_SET_STATUS", commit=False)
                self.files.conn.commit()
                return ok(updated=len(file_ids), total=len(paths))
                
            except (sqlite3.DatabaseError, sqlite3.OperationalError) as inner_e:
                # BUG #8 FIX: Rollback on any inner error
                logger.error(f"Database error during batch update, rolling back: {inner_e}")
                try:
                    self.files.conn.rollback()
                except (sqlite3.Error, RuntimeError):
                    logger.debug("Error during rollback", exc_info=True)
                raise
            except (KeyError, ValueError, TypeError) as inner_e:
                logger.error(f"Invalid data during batch update, rolling back: {inner_e}")
                try:
                    self.files.conn.rollback()
                except (sqlite3.Error, RuntimeError):
                    logger.debug("Error during rollback", exc_info=True)
                raise
        
        except PermissionError as e:
            return err("PERMISSION_DENIED", str(e))
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Database error in batch status update: {e}")
            return err("DATABASE_ERROR", "Database operation failed")
        except Exception as e:
            logger.error(f"Batch status update failed: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    # --- Lock toggle ---
    def ui_toggle_lock(self, path: Path) -> dict:
        try:
            locked = self.status_svc.toggle_lock(path, action_id="LOCK_TOGGLE")
            return ok(locked=locked)
        except PermissionError as e:
            return err("PERMISSION_DENIED", str(e))
        except (KeyError, ValueError) as e:
            return err("INVALID_PATH", str(e))
        except OSError as e:
            return err("FILE_ERROR", str(e))
        except Exception as e:
            logger.error(f"Unexpected error in ui_toggle_lock: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    # --- Batch delete ---
    def ui_batch_delete(self, paths: List[Path]) -> dict:
        if not paths:
            return ok(deleted_ids=[], skipped_locked=[])
        try:
            # Resolve file_ids
            cur = self.files.conn.execute(
                f"SELECT file_id, path, is_locked FROM files WHERE path IN ({','.join('?' for _ in paths)})",
                [str(p) for p in paths],
            )
            rows = cur.fetchall()
            locked = [r[1] for r in rows if r[2]]
            ids = [r[0] for r in rows if not r[2]]
            res = self.files.mark_deleted(ids)
            return ok(deleted_ids=res["deleted_ids"], skipped_locked=locked or res["skipped_locked_ids"])
        except PermissionError as e:
            return err("PERMISSION_DENIED", str(e))
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Database error in batch delete: {e}")
            return err("DATABASE_ERROR", "Database operation failed")
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Invalid data in batch delete: {e}")
            return err("INVALID_DATA", str(e))
        except Exception as e:
            logger.error(f"Batch delete failed: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    # --- Rules ---
    def ui_apply_rules(self, rules: Iterable[Callable[[Path, dict], RuleResult | None]]) -> dict:
        try:
            sim = self.rule_sim.simulate(rules)
            # UI shows sim; here we directly apply for this facade method
            self.rule_sim.apply_simulation(sim, action_id="RULE_APPLY")
            skipped = [r for r in sim if r.skip_reason]
            return ok(applied=True, skipped=[{"path": str(r.path), "skip_reason": r.skip_reason} for r in skipped])
        except PermissionError as e:
            return err("PERMISSION_DENIED", str(e))
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid rule data: {e}")
            return err("INVALID_RULES", str(e))
        except Exception as e:
            logger.error(f"Rule application failed: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    # --- Undo ---
    def ui_undo(self) -> dict:
        try:
            success = self.status_svc.undo_last()
            return ok(undone=success)
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Database error during undo: {e}")
            return err("DATABASE_ERROR", "Undo operation failed")
        except Exception as e:
            logger.error(f"Undo operation failed: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    # --- Progress ---
    def ui_get_progress(self) -> dict:
        try:
            return ok(**self.progress_svc.snapshot())
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Invalid progress data: {e}")
            return err("INVALID_STATE", str(e))
        except Exception as e:
            logger.error(f"Progress snapshot failed: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    def ui_get_active_progress(self) -> dict:
        try:
            return ok(**self.progress_svc.snapshot_active())
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Invalid active progress data: {e}")
            return err("INVALID_STATE", str(e))
        except Exception as e:
            logger.error(f"Active progress snapshot failed: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    # --- Capabilities ---
    def ui_get_capabilities(self) -> dict:
        try:
            return ok(**self.mode_svc.get_capabilities())
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Invalid capabilities data: {e}")
            return err("INVALID_STATE", str(e))
        except Exception as e:
            logger.error(f"Capabilities query failed: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    # --- Filters ---
    def ui_list_unsure(self) -> dict:
        try:
            paths = self.files.list_by_status([FileStatus.UNSURE])
            return ok(paths=[str(p) for p in paths])
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Database error listing unsure files: {e}")
            return err("DATABASE_ERROR", "Failed to list files")
        except Exception as e:
            logger.error(f"List unsure failed: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    def ui_list_undecided(self) -> dict:
        try:
            paths = self.files.list_by_status([FileStatus.UNDECIDED])
            return ok(paths=[str(p) for p in paths])
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Database error listing undecided files: {e}")
            return err("DATABASE_ERROR", "Failed to list files")
        except Exception as e:
            logger.error(f"List undecided failed: {e}", exc_info=True)
            return err("UNKNOWN", str(e))

    # --- Maintenance ---
    def ui_clear_cache(self) -> dict:
        """Clear analysis/cache tables for a clean pipeline re-run."""
        try:
            cleared_cache = 0
            if self.cache_manager:
                cleared_cache = self.cache_manager.clear_cache(older_than_days=None)

            conn = self.files.conn
            # Clear incremental analysis caches
            conn.execute("DELETE FROM analysis_cache")
            conn.execute("DELETE FROM file_hash_mapping")
            conn.execute("DELETE FROM file_hashes")
            conn.execute("DELETE FROM scan_history")

            # Clear image_cache table if present
            try:
                conn.execute("DELETE FROM image_cache")
            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                # Table may not exist
                pass

            conn.commit()
            return ok(cleared_cache=cleared_cache)
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Database error clearing cache: {e}")
            try:
                self.files.conn.rollback()
            except (sqlite3.DatabaseError, sqlite3.OperationalError):
                pass
            return err("CACHE_CLEAR_FAILED", "Database error during cache clear")
        except OSError as e:
            logger.error(f"File system error clearing cache: {e}")
            return err("FILE_ERROR", str(e))
        except (ValueError, sqlite3.Error) as e:
            logger.error(f"Cache clear failed: {e}", exc_info=True)
            try:
                self.files.conn.rollback()
            except sqlite3.Error:
                logger.debug("Rollback failed", exc_info=True)
            return err("CACHE_CLEAR_FAILED", str(e))

    def ui_reset_pipeline_state(self) -> dict:
        """Reset pipeline state (groups, decisions, caches) while keeping file index."""
        try:
            conn = self.files.conn

            # Clear duplicate grouping + decision history
            conn.execute("DELETE FROM duplicates")
            conn.execute("DELETE FROM status_history")

            # Clear caches
            conn.execute("DELETE FROM analysis_cache")
            conn.execute("DELETE FROM file_hash_mapping")
            conn.execute("DELETE FROM file_hashes")
            conn.execute("DELETE FROM scan_history")
            try:
                conn.execute("DELETE FROM image_cache")
            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                # Table may not exist
                pass

            # Reset decision state for non-deleted files
            conn.execute(
                """
                UPDATE files
                SET file_status = 'UNDECIDED',
                    decided_at = NULL,
                    is_recommended = 0,
                    keeper_source = 'undecided',
                    is_keeper = 0,
                    phash = NULL,
                    file_hash = NULL,
                    sharpness_score = NULL,
                    overall_score = NULL,
                    quality_score = NULL,
                    exif_json = NULL
                WHERE is_deleted = 0
                """
            )

            conn.commit()
            return ok()
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            # BUG #5 FIX: Proper error propagation with logging and rollback
            logger.error(f"Database error during reset: {e}", exc_info=True)
            try:
                self.files.conn.rollback()
            except (sqlite3.DatabaseError, sqlite3.OperationalError) as rollback_err:
                logger.error(f"Rollback failed: {rollback_err}")
            return err("RESET_FAILED", "Database operation failed during reset")
        except Exception as e:
            # BUG #5 FIX: Proper error propagation with logging and rollback
            logger.error(f"Reset failed: {e}", exc_info=True)
            try:
                self.files.conn.rollback()
            except Exception as rollback_err:
                logger.error(f"Rollback failed: {rollback_err}")
            # Propagate error to caller with detailed context
            return err("RESET_FAILED", f"Pipeline reset failed: {str(e)}")
    
    # --- PHASE 4 FIX 3: Best Photos API ---
    def ui_get_best_photos(self, top_n: int = 100) -> dict:
        """Get best N photos across entire library using absolute ranking.
        
        Uses cache top_n_flag entries to find highest-quality photos library-wide.
        Falls back to quality_score-based ranking if insufficient top_n entries exist.
        
        Args:
            top_n: Number of top photos to return (default 100)
            
        Returns:
            Dict with ranked photos: {"ok": True, "photos": [{"hash", "score"}]}
        """
        try:
            if not self.cache_manager:
                return err("NO_CACHE", "Cache manager not available")
            
            # Strategy: Query top_n_flag entries from cache (marked as best in each group)
            # Then expand with high-score entries to reach requested limit
            
            top_entries = self.cache_manager.get_top_n_entries(limit=top_n * 2)  # Get extra for safety
            
            if not top_entries:
                # Fallback: Get entries by quality score range
                top_entries = self.cache_manager.get_entries_by_quality_range(
                    min_score=70.0,  # High quality threshold
                    max_score=100.0
                )
            
            if not top_entries:
                return ok(photos=[], message="No high-quality photos found in cache")
            
            # Sort by quality score (descending) and limit
            sorted_entries = sorted(top_entries, key=lambda x: x.get("quality_score", 0), reverse=True)
            best_entries = sorted_entries[:top_n]
            
            # Format response
            photos = [
                {
                    "hash": entry["hash"],
                    "score": round(entry["quality_score"], 2),
                    "timestamp": entry.get("timestamp", 0),
                }
                for entry in best_entries
            ]
            
            return ok(photos=photos, count=len(photos))
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Invalid cache data in best photos: {e}")
            return err("INVALID_DATA", f"Invalid cache data: {str(e)}")
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Database error retrieving best photos: {e}")
            return err("DATABASE_ERROR", "Failed to retrieve ranking data")
        except Exception as e:
            logger.error(f"Best photos API failed: {e}", exc_info=True)
            return err("RANKING_FAILED", f"Failed to rank photos: {str(e)}")
