from __future__ import annotations

import sqlite3
from pathlib import Path

from photo_cleaner.ui.map.map_widget import MapWidget


def test_load_markers_from_db_returns_keep_files_only(tmp_path: Path) -> None:
    db_path = tmp_path / "map.sqlite"
    with sqlite3.connect(db_path) as con:
        con.executescript(
            """
            CREATE TABLE files (
                file_id INTEGER PRIMARY KEY,
                path TEXT NOT NULL,
                quality_score REAL,
                exif_location_name TEXT,
                file_status TEXT NOT NULL DEFAULT 'UNDECIDED',
                is_deleted BOOLEAN DEFAULT 0
            );

            CREATE TABLE geo_groups (
                id INTEGER PRIMARY KEY,
                latitude REAL,
                longitude REAL
            );

            CREATE TABLE geo_group_images (
                id INTEGER PRIMARY KEY,
                geo_group_id INTEGER NOT NULL,
                file_id INTEGER NOT NULL
            );
            """
        )

        con.execute(
            "INSERT INTO files (file_id, path, quality_score, exif_location_name, file_status, is_deleted) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "C:/photos/keep.jpg", 91.0, "Berlin, Germany", "KEEP", 0),
        )
        con.execute(
            "INSERT INTO files (file_id, path, quality_score, exif_location_name, file_status, is_deleted) VALUES (?, ?, ?, ?, ?, ?)",
            (2, "C:/photos/delete.jpg", 75.0, "Berlin, Germany", "DELETE", 0),
        )
        con.execute(
            "INSERT INTO files (file_id, path, quality_score, exif_location_name, file_status, is_deleted) VALUES (?, ?, ?, ?, ?, ?)",
            (3, "C:/photos/deleted_keep.jpg", 99.0, "Berlin, Germany", "KEEP", 1),
        )
        con.execute(
            "INSERT INTO geo_groups (id, latitude, longitude) VALUES (?, ?, ?)",
            (10, 52.52, 13.405),
        )
        con.executemany(
            "INSERT INTO geo_group_images (geo_group_id, file_id) VALUES (?, ?)",
            [(10, 1), (10, 2), (10, 3)],
        )
        con.commit()

    dummy = MapWidget.__new__(MapWidget)
    dummy._db_path = db_path

    markers = MapWidget._load_markers_from_db(dummy)

    assert len(markers) == 1
    assert markers[0].file_id == 1
    assert markers[0].path == "C:/photos/keep.jpg"
    assert markers[0].location_name == "Berlin, Germany"