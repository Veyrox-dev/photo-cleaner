from pathlib import Path

from photo_cleaner.config import AppConfig
from photo_cleaner.models.status import FileStatus

from tests.unit.test_services_guards import make_services, seed_file, setup_db


def test_clear_cache_removes_user_cache_files(tmp_path):
    conn = setup_db(tmp_path)
    _, _, _, _, _, _, ui = make_services(conn)

    original_user_data_dir = AppConfig._user_data_dir
    user_data_dir = tmp_path / "user-data"
    AppConfig.set_user_data_dir(user_data_dir)
    cache_dir = AppConfig.get_cache_dir()
    thumb_dir = cache_dir / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    (thumb_dir / "thumb-a.png").write_bytes(b"thumb")
    (cache_dir / "temp.txt").write_text("cache", encoding="utf-8")

    try:
        result = ui.ui_clear_cache()

        assert result["ok"] is True
        assert result["cleared_disk_cache_files"] == 2
        assert not any(cache_dir.rglob("*.*"))
    finally:
        AppConfig._user_data_dir = original_user_data_dir


def test_reset_pipeline_clears_groups_and_decisions(tmp_path):
    conn = setup_db(tmp_path)
    file_id = seed_file(conn, "reset-me.jpg", status=FileStatus.KEEP, group_id="grp-1")
    _, _, _, _, _, _, ui = make_services(conn)

    conn.execute(
        "INSERT INTO analysis_cache (hash_key, file_hash, quality_score) VALUES (?, ?, ?)",
        ("hash-1", "file-hash-1", 87.0),
    )
    conn.execute(
        "INSERT INTO file_hash_mapping (file_id, hash_key, file_path) VALUES (?, ?, ?)",
        (file_id, "hash-1", str(Path("reset-me.jpg").resolve())),
    )
    conn.execute(
        "INSERT INTO status_history (action_id, file_id, file_path, old_status, new_status, old_locked, new_locked, old_decided_at, new_decided_at, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("STATUS_CHANGE", file_id, str(Path("reset-me.jpg").resolve()), "UNDECIDED", "KEEP", 0, 0, None, 1.0, "test"),
    )
    conn.execute(
        "UPDATE files SET quality_score = 91.0, sharpness_score = 80.0, overall_score = 92.0, keeper_source = 'auto', is_keeper = 1 WHERE file_id = ?",
        (file_id,),
    )
    conn.commit()

    result = ui.ui_reset_pipeline_state()

    assert result["ok"] is True
    assert conn.execute("SELECT COUNT(*) FROM duplicates").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM status_history").fetchone()[0] == 0
    row = conn.execute(
        "SELECT file_status, decided_at, is_recommended, keeper_source, is_keeper, quality_score, overall_score FROM files WHERE file_id = ?",
        (file_id,),
    ).fetchone()
    assert tuple(row) == ("UNDECIDED", None, 0, "undecided", 0, None, None)