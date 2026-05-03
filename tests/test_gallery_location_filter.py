"""Tests for Phase 4A location filtering in GalleryView."""

import sqlite3
import tempfile
from pathlib import Path

from photo_cleaner.ui.gallery.gallery_filter_bar import GalleryFilterOptions
from photo_cleaner.ui.gallery.gallery_view import GalleryEntry, GalleryView


def _entry(path_name: str, location_name: str | None) -> GalleryEntry:
    return GalleryEntry(
        path=Path(f"/tmp/{path_name}"),
        quality_score=80.0,
        sharpness_component=0.8,
        lighting_component=0.8,
        resolution_component=0.8,
        face_quality_component=None,
        capture_time=None,
        exif_json=None,
        location_name=location_name,
    )


def _build_view(entries: list[GalleryEntry]) -> GalleryView:
    view = GalleryView.__new__(GalleryView)
    view._all_entries = entries
    view._filtered_entries = []
    view._render_current_page = lambda: None
    return view


def test_location_filter_substring_match() -> None:
    view = _build_view(
        [
            _entry("a.jpg", "New York, USA"),
            _entry("b.jpg", "Berlin, Deutschland"),
        ]
    )
    opts = GalleryFilterOptions(location_query="York")

    view._apply_filter(opts)

    assert len(view._filtered_entries) == 1
    assert view._filtered_entries[0].location_name == "New York, USA"


def test_location_filter_case_insensitive() -> None:
    view = _build_view([_entry("a.jpg", "Berlin, Deutschland")])
    opts = GalleryFilterOptions(location_query="berLIN")

    view._apply_filter(opts)

    assert len(view._filtered_entries) == 1


def test_location_filter_no_match() -> None:
    view = _build_view([_entry("a.jpg", "Paris, France")])
    opts = GalleryFilterOptions(location_query="Tokyo")

    view._apply_filter(opts)

    assert len(view._filtered_entries) == 0


def test_location_filter_excludes_none_locations() -> None:
    view = _build_view(
        [
            _entry("a.jpg", None),
            _entry("b.jpg", "Hamburg, Deutschland"),
        ]
    )
    opts = GalleryFilterOptions(location_query="ham")

    view._apply_filter(opts)

    assert len(view._filtered_entries) == 1
    assert view._filtered_entries[0].path.name == "b.jpg"


def test_query_gallery_images_falls_back_to_undecided_when_no_keep() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "gallery.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE files (
                path TEXT,
                quality_score REAL,
                sharpness_component REAL,
                lighting_component REAL,
                resolution_component REAL,
                face_quality_component REAL,
                capture_time REAL,
                modified_time REAL,
                exif_json TEXT,
                exif_location_name TEXT,
                file_status TEXT,
                is_deleted INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            "INSERT INTO files (path, file_status, is_deleted) VALUES (?, ?, 0)",
            (str(Path(tmpdir) / "undecided.jpg"), "UNDECIDED"),
        )
        conn.commit()
        conn.close()

        gallery = GalleryView.__new__(GalleryView)
        gallery._db_path = db_path

        entries = GalleryView._query_gallery_images(gallery)

        assert len(entries) == 1
        assert entries[0].path.name == "undecided.jpg"


def test_query_gallery_images_prefers_keep_when_available() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "gallery.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE files (
                path TEXT,
                quality_score REAL,
                sharpness_component REAL,
                lighting_component REAL,
                resolution_component REAL,
                face_quality_component REAL,
                capture_time REAL,
                modified_time REAL,
                exif_json TEXT,
                exif_location_name TEXT,
                file_status TEXT,
                is_deleted INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            "INSERT INTO files (path, file_status, is_deleted) VALUES (?, ?, 0)",
            (str(Path(tmpdir) / "keep.jpg"), "KEEP"),
        )
        conn.execute(
            "INSERT INTO files (path, file_status, is_deleted) VALUES (?, ?, 0)",
            (str(Path(tmpdir) / "undecided.jpg"), "UNDECIDED"),
        )
        conn.commit()
        conn.close()

        gallery = GalleryView.__new__(GalleryView)
        gallery._db_path = db_path

        entries = GalleryView._query_gallery_images(gallery)

        assert len(entries) == 1
        assert entries[0].path.name == "keep.jpg"