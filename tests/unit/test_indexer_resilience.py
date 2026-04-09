from pathlib import Path

from photo_cleaner.core.indexer import PhotoIndexer
from photo_cleaner.db.schema import Database
from photo_cleaner.duplicates.finder import DuplicateFinder


def test_process_file_keeps_record_when_only_file_hash_exists(monkeypatch, tmp_path):
    class StubHasher:
        def compute_all_hashes(self, _path):
            return {"phash": None, "file_hash": "abc123"}

    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"data")

    monkeypatch.setattr("photo_cleaner.core.indexer.ImageHasher", StubHasher)
    monkeypatch.setattr("photo_cleaner.core.indexer.PhotoIndexer._extract_capture_time", lambda _p: 1234.0)

    result = PhotoIndexer._process_file(image_path)

    assert result is not None
    assert result["phash"] is None
    assert result["file_hash"] == "abc123"
    assert result["capture_time"] == 1234.0


def test_duplicate_finder_falls_back_to_exact_file_hash_groups(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.connect()

    cursor = db.conn.cursor()
    cursor.executemany(
        """
        INSERT INTO files (path, phash, file_hash, file_size, modified_time, created_time)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (str(tmp_path / "a.jpg"), None, "same-hash", 1, 1.0, 1.0),
            (str(tmp_path / "b.jpg"), None, "same-hash", 1, 1.0, 1.0),
            (str(tmp_path / "c.jpg"), None, "other-hash", 1, 1.0, 1.0),
        ],
    )
    db.conn.commit()

    finder = DuplicateFinder(db, phash_threshold=10)
    groups = finder.build_groups()

    assert len(groups) == 1
    assert groups[0][1] == 2

    cursor.execute("SELECT COUNT(*) FROM duplicates")
    assert cursor.fetchone()[0] == 2


def test_duplicate_finder_time_window_relaxes_similarity(monkeypatch, tmp_path):
    db_path = tmp_path / "test_relaxed_time.db"
    db = Database(db_path)
    db.connect()

    # 32-bit Hamming distance (50% similarity): should NOT match with strict threshold=10.
    phash_a = "0000000000000000"
    phash_b = "ffffffff00000000"

    cursor = db.conn.cursor()
    cursor.executemany(
        """
        INSERT INTO files (path, phash, file_hash, file_size, capture_time, modified_time, created_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (str(tmp_path / "a.jpg"), phash_a, "ha", 1, 1000.0, 1000.0, 1000.0),
            (str(tmp_path / "b.jpg"), phash_b, "hb", 1, 1015.0, 1015.0, 1015.0),
        ],
    )
    db.conn.commit()

    monkeypatch.setenv("PHOTOCLEANER_GROUP_TIME_WINDOW_SEC", "30")
    monkeypatch.setenv("PHOTOCLEANER_GROUP_RELAXED_SIMILARITY", "0.50")

    finder = DuplicateFinder(db, phash_threshold=10)
    groups = finder.build_groups()

    assert len(groups) == 1
    assert groups[0][1] == 2


def test_duplicate_finder_time_window_respects_distance_limit(monkeypatch, tmp_path):
    db_path = tmp_path / "test_relaxed_limit.db"
    db = Database(db_path)
    db.connect()

    # 64-bit Hamming distance (0% similarity): must never group even in time window.
    phash_a = "0000000000000000"
    phash_b = "ffffffffffffffff"

    cursor = db.conn.cursor()
    cursor.executemany(
        """
        INSERT INTO files (path, phash, file_hash, file_size, capture_time, modified_time, created_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (str(tmp_path / "c.jpg"), phash_a, "hc", 1, 2000.0, 2000.0, 2000.0),
            (str(tmp_path / "d.jpg"), phash_b, "hd", 1, 2005.0, 2005.0, 2005.0),
        ],
    )
    db.conn.commit()

    monkeypatch.setenv("PHOTOCLEANER_GROUP_TIME_WINDOW_SEC", "30")
    monkeypatch.setenv("PHOTOCLEANER_GROUP_RELAXED_SIMILARITY", "0.60")

    finder = DuplicateFinder(db, phash_threshold=10)
    groups = finder.build_groups()

    assert groups == []
