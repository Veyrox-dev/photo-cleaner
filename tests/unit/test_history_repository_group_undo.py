import sqlite3

from photo_cleaner.repositories.history_repository import HistoryRepository


CREATE_FILES = """
CREATE TABLE files (
    file_id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    file_status TEXT,
    is_locked BOOLEAN,
    decided_at REAL,
    is_deleted BOOLEAN DEFAULT 0
);
"""

CREATE_STATUS_HISTORY = """
CREATE TABLE status_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    old_locked BOOLEAN,
    new_locked BOOLEAN,
    old_decided_at REAL,
    new_decided_at REAL,
    reason TEXT,
    created_at REAL
);
"""

CREATE_DUPLICATES = """
CREATE TABLE duplicates (
    duplicate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    similarity_score REAL,
    is_keeper BOOLEAN DEFAULT 0
);
"""


def _setup_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(CREATE_FILES)
    conn.execute(CREATE_STATUS_HISTORY)
    conn.execute(CREATE_DUPLICATES)
    conn.execute(
        "INSERT INTO files (file_id, path, file_status, is_locked, decided_at, is_deleted) VALUES (1, 'a.jpg', 'UNDECIDED', 0, NULL, 0)"
    )
    conn.execute(
        "INSERT INTO files (file_id, path, file_status, is_locked, decided_at, is_deleted) VALUES (2, 'b.jpg', 'UNDECIDED', 0, NULL, 0)"
    )
    conn.execute(
        "INSERT INTO duplicates (group_id, file_id, similarity_score, is_keeper) VALUES ('G1', 1, 0.95, 0)"
    )
    conn.commit()
    return conn


def test_undo_group_reassignment_restores_original_group() -> None:
    conn = _setup_conn()
    history = HistoryRepository(conn)

    # Simulate merge result in DB.
    conn.execute("UPDATE duplicates SET group_id = 'MERGED_1' WHERE file_id = 1")
    conn.execute(
        "INSERT INTO duplicates (group_id, file_id, similarity_score, is_keeper) VALUES ('MERGED_1', 2, 1.0, 0)"
    )

    action_id = "GROUP_MERGE_1"
    history.record_group_reassignment(
        action_id=action_id,
        file_id=1,
        old_group_id="G1",
        new_group_id="MERGED_1",
        reason="source=test",
    )
    history.record_group_reassignment(
        action_id=action_id,
        file_id=2,
        old_group_id=None,
        new_group_id="MERGED_1",
        reason="source=test",
    )
    conn.commit()

    assert history.undo_last_action() is True

    group_1 = conn.execute("SELECT group_id FROM duplicates WHERE file_id = 1").fetchone()
    group_2 = conn.execute("SELECT group_id FROM duplicates WHERE file_id = 2").fetchone()

    assert group_1 is not None
    assert group_1[0] == "G1"
    assert group_2 is None


def test_undo_regular_status_action_still_works() -> None:
    conn = _setup_conn()
    history = HistoryRepository(conn)

    conn.execute("UPDATE files SET file_status = 'KEEP' WHERE file_id = 1")
    conn.execute(
        """
        INSERT INTO status_history (action_id, file_id, file_path, old_status, new_status, old_locked, new_locked, old_decided_at, new_decided_at, reason)
        VALUES ('MANUAL_1', 1, 'a.jpg', 'UNDECIDED', 'KEEP', 0, 0, NULL, 123.0, 'manual test')
        """
    )
    conn.commit()

    assert history.undo_last_action() is True
    status = conn.execute("SELECT file_status FROM files WHERE file_id = 1").fetchone()
    assert status is not None
    assert status[0] == 'UNDECIDED'


def test_undo_group_split_restores_original_group() -> None:
    conn = _setup_conn()
    history = HistoryRepository(conn)

    conn.execute(
        "INSERT INTO duplicates (group_id, file_id, similarity_score, is_keeper) VALUES ('G1', 2, 0.90, 0)"
    )
    conn.execute("UPDATE duplicates SET group_id = 'SPLIT_1' WHERE file_id = 2")

    action_id = "GROUP_SPLIT_1"
    history.record_group_reassignment(
        action_id=action_id,
        file_id=2,
        old_group_id="G1",
        new_group_id="SPLIT_1",
        reason="source=test",
    )
    conn.commit()

    assert history.undo_last_action() is True

    group_2 = conn.execute("SELECT group_id FROM duplicates WHERE file_id = 2").fetchone()
    assert group_2 is not None
    assert group_2[0] == "G1"


def test_describe_last_action_for_group_split() -> None:
    conn = _setup_conn()
    history = HistoryRepository(conn)

    history.record_group_reassignment(
        action_id="GROUP_SPLIT_2",
        file_id=1,
        old_group_id="G1",
        new_group_id="SPLIT_2",
        reason="source=split",
    )
    conn.commit()

    description = history.describe_last_action()

    assert description is not None
    assert description["kind"] == "group_split"
    assert description["count"] == 1


def test_recent_actions_returns_latest_first() -> None:
    conn = _setup_conn()
    history = HistoryRepository(conn)

    history.record_group_reassignment(
        action_id="GROUP_MERGE_2",
        file_id=1,
        old_group_id="G1",
        new_group_id="MERGED_2",
        reason="source=merge",
    )
    conn.execute(
        """
        INSERT INTO status_history (action_id, file_id, file_path, old_status, new_status, old_locked, new_locked, old_decided_at, new_decided_at, reason)
        VALUES ('MANUAL_2', 1, 'a.jpg', 'UNDECIDED', 'KEEP', 0, 0, NULL, 123.0, 'manual test')
        """
    )
    conn.commit()

    recent = history.recent_actions(limit=2)

    assert len(recent) == 2
    assert recent[0]["action_id"] == "MANUAL_2"
    assert recent[0]["kind"] == "status_change"
    assert recent[1]["action_id"] == "GROUP_MERGE_2"
    assert recent[1]["kind"] == "group_merge"
