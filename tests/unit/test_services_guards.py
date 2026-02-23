import sqlite3
import time
from pathlib import Path

import pytest

from photo_cleaner.db.schema import Database
from photo_cleaner.models.mode import AppMode
from photo_cleaner.models.status import FileStatus
from photo_cleaner.repositories.file_repository import FileRepository
from photo_cleaner.repositories.history_repository import HistoryRepository
from photo_cleaner.services.mode_service import ModeService
from photo_cleaner.services.progress_service import ProgressService
from photo_cleaner.services.rule_simulator import RuleResult, RuleSimulator
from photo_cleaner.services.status_service import StatusService
from photo_cleaner.ui_actions import UIActions


# Helpers

def setup_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    conn = db.connect()
    return conn


def seed_file(conn: sqlite3.Connection, path: str, *, status: FileStatus = FileStatus.UNDECIDED, locked: bool = False, is_deleted: bool = False, file_hash: str | None = None, phash: str | None = None, group_id: str | None = None, size: int = 100) -> int:
    safe_path = str(Path(path).resolve())
    cur = conn.execute(
        """
        INSERT INTO files (path, file_status, is_locked, is_deleted, file_hash, phash, file_size)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (safe_path, status.value, int(locked), int(is_deleted), file_hash, phash, size),
    )
    file_id = cur.lastrowid
    if group_id is not None:
        conn.execute(
            "INSERT INTO duplicates (group_id, file_id, similarity_score) VALUES (?, ?, 0.0)",
            (group_id, file_id),
        )
    conn.commit()
    return file_id


def make_services(conn: sqlite3.Connection, mode: AppMode = AppMode.SAFE_MODE, is_exact_map: dict[str, bool] | None = None):
    files = FileRepository(conn)
    history = HistoryRepository(conn)
    mode_svc = ModeService(conn)
    mode_svc.set_mode(mode)
    progress = ProgressService(files)
    exact_map = is_exact_map or {}
    is_exact = lambda p: exact_map.get(str(p), False)
    rule_sim = RuleSimulator(files, image_meta_loader=lambda _p: {}, mode_getter=mode_svc.get_mode, is_exact_duplicate=is_exact)
    status_svc = StatusService(files, history, mode_svc.get_mode, is_exact_duplicate=is_exact)
    ui = UIActions(files, history, mode_svc, progress, rule_sim, status_svc)
    return files, history, mode_svc, progress, rule_sim, status_svc, ui


# A. Status & decided_at

def test_decided_at_rules(tmp_path):
    conn = setup_db(tmp_path)
    path = "a.jpg"
    seed_file(conn, path)
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn)
    safe_path = str(Path(path).resolve())

    status_svc.set_status(Path(path), FileStatus.KEEP)
    cur = conn.execute("SELECT decided_at FROM files WHERE path=?", (safe_path,))
    keep_ts = cur.fetchone()[0]
    assert keep_ts is not None

    status_svc.set_status(Path(path), FileStatus.DELETE)
    cur = conn.execute("SELECT decided_at FROM files WHERE path=?", (safe_path,))
    del_ts = cur.fetchone()[0]
    assert del_ts is not None and del_ts >= keep_ts

    status_svc.set_status(Path(path), FileStatus.UNSURE)
    cur = conn.execute("SELECT decided_at FROM files WHERE path=?", (safe_path,))
    assert cur.fetchone()[0] is None

    status_svc.set_status(Path(path), FileStatus.UNDECIDED)
    cur = conn.execute("SELECT decided_at FROM files WHERE path=?", (safe_path,))
    assert cur.fetchone()[0] is None


def test_toggle_lock_keeps_status_and_history(tmp_path):
    conn = setup_db(tmp_path)
    path = "b.jpg"
    seed_file(conn, path, status=FileStatus.UNDECIDED)
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn)
    safe_path = str(Path(path).resolve())

    locked = status_svc.toggle_lock(Path(path), lock=True)
    assert locked is True
    cur = conn.execute("SELECT file_status, is_locked FROM files WHERE path=?", (safe_path,))
    s, l = cur.fetchone()
    assert s == FileStatus.UNDECIDED.value and l == 1

    # history recorded
    cur = conn.execute("SELECT action_id FROM status_history ORDER BY history_id DESC LIMIT 1")
    assert cur.fetchone()[0] == "LOCK_TOGGLE"

    # undo reverts lock
    assert status_svc.undo_last() is True
    cur = conn.execute("SELECT is_locked FROM files WHERE path=?", (safe_path,))
    assert cur.fetchone()[0] == 0


# B. SAFE_MODE guards

def test_safe_mode_blocks_delete_non_exact(tmp_path):
    conn = setup_db(tmp_path)
    path = "c.jpg"
    seed_file(conn, path)
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn, mode=AppMode.SAFE_MODE, is_exact_map={str(Path(path)): False})
    res = ui.ui_set_delete(Path(path))
    assert res["ok"] is False and res["error"] == "SAFE_MODE_BLOCKED"


def test_safe_mode_allows_delete_exact(tmp_path):
    conn = setup_db(tmp_path)
    path = "d.jpg"
    seed_file(conn, path)
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn, mode=AppMode.SAFE_MODE, is_exact_map={str(Path(path)): True})
    res = ui.ui_set_delete(Path(path))
    assert res["ok"] is True


# C. LOCK guards

def test_lock_blocks_delete_and_rules(tmp_path):
    conn = setup_db(tmp_path)
    path = "e.jpg"
    seed_file(conn, path, locked=True)
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn, is_exact_map={str(Path(path)): True})

    res = ui.ui_set_delete(Path(path))
    assert res["ok"] is False and res["error"] == "FILE_LOCKED"

    # rule simulate should skip locked
    def rule(_p, _m):
        return RuleResult(path=Path(path), suggested_status=FileStatus.DELETE, reason="test")

    sim = rule_sim.simulate([rule])
    assert sim and sim[0].skip_reason == "SKIPPED_LOCKED"


# D. Batch operations

def test_bulk_set_and_history(tmp_path):
    conn = setup_db(tmp_path)
    p1, p2 = "f1.jpg", "f2.jpg"
    id1 = seed_file(conn, p1)
    id2 = seed_file(conn, p2)
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn)

    files.bulk_set_status([id1, id2], FileStatus.KEEP, action_id="BATCH_TEST")
    cur = conn.execute("SELECT file_status, decided_at FROM files WHERE file_id IN (?,?)", (id1, id2))
    rows = cur.fetchall()
    assert all(r[0] == FileStatus.KEEP.value and r[1] is not None for r in rows)
    cur = conn.execute("SELECT DISTINCT action_id FROM status_history WHERE action_id='BATCH_TEST'")
    assert cur.fetchone()[0] == "BATCH_TEST"


def test_mark_deleted_reports_locked(tmp_path):
    conn = setup_db(tmp_path)
    id1 = seed_file(conn, "g1.jpg", locked=True)
    id2 = seed_file(conn, "g2.jpg", locked=False)
    files, *_ = make_services(conn)
    res = files.mark_deleted([id1, id2])
    assert res["deleted_ids"] == [id2]
    assert res["skipped_locked_ids"] == [id1]


# E. RuleSimulator apply & undo

def test_rule_apply_and_undo(tmp_path):
    conn = setup_db(tmp_path)
    path = "h.jpg"
    seed_file(conn, path)
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn, mode=AppMode.CLEANUP_MODE)
    safe_path = str(Path(path).resolve())

    def rule(_p, _m):
        return RuleResult(path=Path(path), suggested_status=FileStatus.DELETE, reason="rule")

    sim = rule_sim.simulate([rule])
    assert sim and sim[0].skip_reason is None
    rule_sim.apply_simulation(sim, action_id="RULE_APPLY")
    cur = conn.execute("SELECT file_status, decided_at FROM files WHERE path=?", (safe_path,))
    s, ts = cur.fetchone()
    assert s == FileStatus.DELETE.value and ts is not None

    # undo rule action
    assert status_svc.undo_last() is True
    cur = conn.execute("SELECT file_status FROM files WHERE path=?", (safe_path,))
    assert cur.fetchone()[0] == FileStatus.UNDECIDED.value


# F. ProgressService

def test_progress_counts_and_groups(tmp_path):
    conn = setup_db(tmp_path)
    id1 = seed_file(conn, "i1.jpg", status=FileStatus.DELETE, size=200, group_id="g1", file_hash="h1")
    id2 = seed_file(conn, "i2.jpg", status=FileStatus.UNSURE, size=100, group_id="g1", file_hash="h2")
    id3 = seed_file(conn, "i3.jpg", status=FileStatus.KEEP, size=50, group_id="g2", file_hash="h3")
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn)

    snap = progress.snapshot()
    assert snap["files_total"] == 3
    assert snap["files_unsure"] == 1
    assert snap["files_decided"] == 2  # DELETE+KEEP counted decided
    assert snap["files_open"] == 1
    assert snap["reclaim_bytes"] == 200
    assert snap["groups_total"] == 2
    assert snap["groups_done"] == 1  # g1 has UNSURE, g2 is decided


# G. UI-Facade responses

def test_ui_facade_basic(tmp_path):
    conn = setup_db(tmp_path)
    p = "j.jpg"
    seed_file(conn, p)
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn, mode=AppMode.SAFE_MODE, is_exact_map={p: True})

    r1 = ui.ui_set_keep(Path(p))
    assert r1["ok"] is True

    r2 = ui.ui_set_delete(Path(p))
    assert r2["ok"] is True

    r3 = ui.ui_toggle_lock(Path(p))
    assert r3["ok"] is True and "locked" in r3

    prog = ui.ui_get_progress()
    assert prog["ok"] is True and "files_total" in prog

    caps = ui.ui_get_capabilities()
    assert caps["ok"] is True and "can_delete" in caps

    unsure_list = ui.ui_list_unsure()
    assert unsure_list["ok"] is True


# H. Edge cases: undo stack action-level

def test_undo_action_level(tmp_path):
    conn = setup_db(tmp_path)
    p1, p2 = "k1.jpg", "k2.jpg"
    seed_file(conn, p1)
    seed_file(conn, p2)
    files, history, mode_svc, progress, rule_sim, status_svc, ui = make_services(conn)

    # two files in one action
    status_svc.set_status(Path(p1), FileStatus.KEEP, action_id="ACT1")
    status_svc.set_status(Path(p2), FileStatus.DELETE, action_id="ACT1")
    assert status_svc.undo_last() is True
    cur = conn.execute("SELECT file_status FROM files WHERE path IN (?,?)", (p1, p2))
    assert all(r[0] == FileStatus.UNDECIDED.value for r in cur.fetchall())
