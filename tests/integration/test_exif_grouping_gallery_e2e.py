"""Integration test: EXIF grouping writes to DB and is visible in GalleryView."""

import tempfile
from datetime import datetime
from pathlib import Path

from photo_cleaner.db.schema import Database
from photo_cleaner.exif.exif_grouping_engine import ExifGroupingEngine
from photo_cleaner.exif.geocoding_cache import GeocodingCache
from photo_cleaner.ui.gallery.gallery_view import GalleryView


class _StubGeocoder:
    def reverse_geocode(self, lat: float, lon: float) -> dict:
        return {
            "city": "New York",
            "country": "USA",
            "cached_at": datetime.now().isoformat(),
        }


def test_exif_grouping_result_is_visible_in_gallery(monkeypatch) -> None:
    """EXIF -> group_images() -> DB -> Gallery snippet includes location."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "gallery.db"
        image_path = tmp_path / "image_001.jpg"
        image_path.touch()

        database = Database(db_path)
        conn = database.connect()
        conn.execute(
            """
            INSERT INTO files (path, file_status, quality_score, capture_time, exif_json, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(image_path),
                "KEEP",
                91.5,
                datetime(2024, 5, 2, 12, 0, 0).timestamp(),
                '{"Model": "Sony A7IV"}',
                0,
            ),
        )
        conn.commit()
        database.close()

        engine = ExifGroupingEngine(
            db_path=db_path,
            geocoding_cache=GeocodingCache(tmp_path / "cache.db"),
            geocoder=_StubGeocoder(),
        )
        monkeypatch.setattr(
            engine,
            "_read_exif_fields",
            lambda _path: (40.7128, -74.0060, "2026-05-02", "Sony A7IV"),
        )

        engine.group_images([image_path], scan_session_id="scan-e2e")

        gallery = GalleryView.__new__(GalleryView)
        gallery._db_path = db_path
        entries = GalleryView._query_keep_images(gallery)

        assert len(entries) == 1
        assert entries[0].location_name == "New York, USA"

        snippet = GalleryView._build_exif_snippet(gallery, entries[0])
        assert snippet == "2024-05-02 | Sony A7IV | New York, USA"