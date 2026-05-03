"""Performance guard for EXIF grouping."""

import sqlite3
import tempfile
import time
from datetime import datetime
from pathlib import Path

from photo_cleaner.db.schema import Database
from photo_cleaner.exif.exif_grouping_engine import ExifGroupingEngine
from photo_cleaner.exif.geocoding_cache import GeocodingCache


class _StubGeocoder:
    def reverse_geocode(self, lat: float, lon: float) -> dict:
        return {
            "city": "Performance City",
            "country": "Testland",
            "cached_at": datetime.now().isoformat(),
        }


def test_grouping_250_images_finishes_under_five_seconds(monkeypatch) -> None:
    """250 Bilder sollen auf Test-Hardware deutlich unter 5s gruppiert werden."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "performance.db"
        database = Database(db_path)
        conn = database.connect()

        image_paths = []
        rows = []
        for index in range(250):
            image_path = tmp_path / f"perf_{index:03d}.jpg"
            image_path.touch()
            image_paths.append(image_path)
            rows.append((str(image_path), "KEEP", 0))

        conn.executemany(
            "INSERT INTO files (path, file_status, is_deleted) VALUES (?, ?, ?)",
            rows,
        )
        conn.commit()
        database.close()

        engine = ExifGroupingEngine(
            db_path=db_path,
            geocoding_cache=GeocodingCache(tmp_path / "perf_cache.db"),
            geocoder=_StubGeocoder(),
        )

        def _fake_read_exif_fields(image_path: Path):
            group_number = int(image_path.stem.split("_")[-1]) % 5
            return (40.7128 + (group_number * 0.001), -74.0060, "2026-05-02", "PerfCam")

        monkeypatch.setattr(engine, "_read_exif_fields", _fake_read_exif_fields)

        start = time.perf_counter()
        engine.group_images(image_paths, scan_session_id="perf-scan")
        elapsed = time.perf_counter() - start

        verify_conn = sqlite3.connect(str(db_path))
        updated_rows = verify_conn.execute(
            "SELECT COUNT(*) FROM files WHERE exif_location_name IS NOT NULL"
        ).fetchone()[0]
        group_rows = verify_conn.execute("SELECT COUNT(*) FROM geo_groups").fetchone()[0]
        verify_conn.close()

        assert elapsed < 5.0
        assert updated_rows == 250
        assert group_rows == 5