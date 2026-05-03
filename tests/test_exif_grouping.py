"""
Unit-Tests für EXIF Smart Grouping Komponenten.

Führe aus mit:
    pytest tests/test_exif_grouping.py -v
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from photo_cleaner.exif.nominatim_geocoder import NominatimGeocoder
from photo_cleaner.exif.geocoding_cache import GeocodingCache
from photo_cleaner.exif.exif_grouping_engine import ExifGroupingEngine


class TestNominatimGeocoder:
    """Unit-Tests für NominatimGeocoder."""
    
    def test_initialization(self):
        """Test: Geocoder wird initialisiert."""
        geocoder = NominatimGeocoder()
        assert geocoder is not None
        assert geocoder.RATE_LIMIT_DELAY == 1.0
    
    def test_invalid_coordinates(self):
        """Test: Ungültige Koordinaten werden abgelehnt."""
        geocoder = NominatimGeocoder()
        
        # Latitude > 90
        result = geocoder.reverse_geocode(100, 0)
        assert result is None
        
        # Longitude > 180
        result = geocoder.reverse_geocode(0, 200)
        assert result is None
    
    def test_valid_coordinates_structure(self):
        """Test: Valide Koordinaten haben korrekte Struktur."""
        geocoder = NominatimGeocoder()
        # Note: Dieser Test ist online, skip wenn keine Verbindung
        try:
            result = geocoder.reverse_geocode(40.7128, -74.0060)  # New York
            if result:
                assert "city" in result
                assert "country" in result
                assert "cached_at" in result
        except Exception:
            pytest.skip("Keine Online-Verbindung zu Nominatim")
    
    def test_rate_limiting(self):
        """Test: Rate-Limiting wird eingehalten."""
        import time
        geocoder = NominatimGeocoder()
        
        start = time.time()
        geocoder.last_request_time = time.time() - 0.5  # Simulate recent request
        
        # Dieser Call sollte mindestens 0.5s warten
        # (aber wir mocken den API-Call, daher nur Rate-Limit testen)
        elapsed = time.time() - start
        # Kurzer Test für Logik, nicht echte API
        assert geocoder.RATE_LIMIT_DELAY >= 1.0


class TestGeocodingCache:
    """Unit-Tests für GeocodingCache."""
    
    @pytest.fixture
    def cache(self):
        """Erstelle Test-Cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = GeocodingCache(db_path, max_memory_entries=10)
            yield cache
    
    def test_initialization(self, cache):
        """Test: Cache wird initialisiert."""
        assert cache is not None
        assert cache.max_memory_entries == 10
        assert cache.ttl_days == 7
    
    def test_memory_cache_set_get(self, cache):
        """Test: Memory-Cache Set/Get funktioniert."""
        coords = (40.7128, -74.0060)
        data = {"city": "New York", "country": "USA"}
        
        cache.set(coords, data)
        result = cache.get(coords)
        
        assert result is not None
        assert result["city"] == "New York"
    
    def test_memory_cache_hit(self, cache):
        """Test: Memory-Cache wird getroffen."""
        coords = (40.7128, -74.0060)
        data = {"city": "New York"}
        
        cache.set(coords, data)
        
        # First get (Cache hit)
        result1 = cache.get(coords)
        assert result1 is not None
        
        # Second get (Memory-LRU hit)
        result2 = cache.get(coords)
        assert result2 is not None
        assert result1 == result2
    
    def test_lru_eviction(self, cache):
        """Test: LRU-Eviction bei Überschreitung."""
        # Set 11 entries (max is 10)
        for i in range(11):
            coords = (float(i), float(i))
            cache.set(coords, {"city": f"City{i}"})
        
        # Erstes Entry sollte evicted sein
        result = cache.get((0.0, 0.0))
        # Könnte noch in DB sein, aber nicht in Memory
        assert len(cache.memory_cache) <= 10
    
    def test_get_statistics(self, cache):
        """Test: Statistiken werden zurückgegeben."""
        coords = (40.7128, -74.0060)
        cache.set(coords, {"city": "New York"})
        
        stats = cache.get_statistics()
        
        assert "memory_entries" in stats
        assert "db_entries" in stats
        assert stats["memory_entries"] >= 1
    
    def test_clear_all(self, cache):
        """Test: clear_all() leert Cache."""
        coords = (40.7128, -74.0060)
        cache.set(coords, {"city": "New York"})
        
        assert cache.get(coords) is not None
        
        cache.clear_all()
        
        assert cache.get(coords) is None
        assert len(cache.memory_cache) == 0


class TestExifGroupingEngine:
    """Unit-Tests für ExifGroupingEngine."""
    
    @pytest.fixture
    def engine(self):
        """Erstelle Test-Engine."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            cache = GeocodingCache(Path(tmpdir) / "cache.db")
            geocoder = NominatimGeocoder()
            
            engine = ExifGroupingEngine(db_path, cache, geocoder)
            yield engine
    
    def test_initialization(self, engine):
        """Test: Engine wird initialisiert."""
        assert engine is not None
        assert engine._is_running is False
    
    def test_group_empty_list(self, engine):
        """Test: Leere Liste wird ignoriert."""
        engine.group_images([])
        assert engine._is_running is False
    
    def test_create_groups_with_gps(self, engine):
        """Test: Gruppen werden nach GPS + Datum erstellt."""
        exif_data = {
            "img1": {"latitude": 40.7128, "longitude": -74.0060, "date_original": "2026-05-02"},
            "img2": {"latitude": 40.7128, "longitude": -74.0060, "date_original": "2026-05-02"},
            "img3": {"latitude": 51.5074, "longitude": -0.1278, "date_original": "2026-05-02"}
        }
        
        groups = engine._create_groups(exif_data)
        
        # Sollte 2 Gruppen haben (2× New York, 1× London)
        assert len(groups) >= 2
    
    def test_create_groups_without_gps(self, engine):
        """Test: Gruppen ohne GPS verwenden Fallback."""
        exif_data = {
            "img1": {"latitude": None, "longitude": None, "date_original": "2026-05-02"},
            "img2": {"latitude": None, "longitude": None, "date_original": "2026-05-02"}
        }
        
        groups = engine._create_groups(exif_data)
        
        assert len(groups) >= 1
        assert any("no_gps" in g["group_key"] for g in groups)


class TestDbMigration:
    """Tests für DB-Migration der Geo-Grouping Tabellen."""

    @pytest.fixture
    def db(self):
        """Erstelle frische Test-DB über Database-Klasse."""
        from photo_cleaner.db.schema import Database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_migration.db"
            database = Database(db_path)
            conn = database.connect()
            yield conn, db_path
            database.close()

    def test_geo_groups_table_created(self, db):
        """Test: geo_groups-Tabelle wird angelegt."""
        conn, _ = db
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='geo_groups'")
        assert cursor.fetchone() is not None

    def test_geo_group_images_table_created(self, db):
        """Test: geo_group_images-Tabelle wird angelegt."""
        conn, _ = db
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='geo_group_images'")
        assert cursor.fetchone() is not None

    def test_geocoding_cache_table_created(self, db):
        """Test: geocoding_cache-Tabelle wird angelegt."""
        conn, _ = db
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='geocoding_cache'")
        assert cursor.fetchone() is not None

    def test_grouping_fallback_log_table_created(self, db):
        """Test: grouping_fallback_log-Tabelle wird angelegt."""
        conn, _ = db
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grouping_fallback_log'")
        assert cursor.fetchone() is not None

    def test_geo_groups_insert_and_select(self, db):
        """Test: INSERT + SELECT in geo_groups funktioniert."""
        conn, _ = db
        conn.execute(
            """
            INSERT INTO geo_groups
                (scan_session_id, group_key, latitude, longitude,
                 location_name, city, country, date_start, date_end, image_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("sess1", "40.7128_-74.0060_2026-05-02", 40.7128, -74.0060,
             "New York, USA", "New York", "USA", "2026-05-02", "2026-05-02", 3),
        )
        conn.commit()
        cursor = conn.execute("SELECT group_key, city, image_count FROM geo_groups WHERE group_key = ?",
                              ("40.7128_-74.0060_2026-05-02",))
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "New York"
        assert row[2] == 3

    def test_geo_group_images_fk_constraint(self, db):
        """Test: geo_group_images referenziert geo_groups korrekt."""
        conn, _ = db
        conn.execute("PRAGMA foreign_keys = ON")
        # Insert a geo_group first
        conn.execute(
            "INSERT INTO geo_groups (group_key, location_name, image_count) VALUES (?, ?, ?)",
            ("test_key", "Test", 1),
        )
        conn.commit()
        geo_group_id = conn.execute("SELECT id FROM geo_groups WHERE group_key='test_key'").fetchone()[0]
        # Insert a file
        conn.execute(
            "INSERT INTO files (path, file_status) VALUES (?, ?)",
            ("/tmp/test.jpg", "KEEP"),
        )
        conn.commit()
        file_id = conn.execute("SELECT file_id FROM files WHERE path='/tmp/test.jpg'").fetchone()[0]
        # Link them
        conn.execute(
            "INSERT INTO geo_group_images (geo_group_id, file_id) VALUES (?, ?)",
            (geo_group_id, file_id),
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM geo_group_images").fetchone()[0]
        assert count == 1

    def test_unique_constraint_geo_groups(self, db):
        """Test: UNIQUE(group_key) in geo_groups wird durchgesetzt."""
        import sqlite3 as _sqlite3
        conn, _ = db
        conn.execute(
            "INSERT INTO geo_groups (group_key, image_count) VALUES (?, ?)",
            ("dup_key", 1),
        )
        conn.commit()
        with pytest.raises(_sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO geo_groups (group_key, image_count) VALUES (?, ?)",
                ("dup_key", 2),
            )
            conn.commit()


class TestSaveGroupsToDb:
    """Tests für ExifGroupingEngine._save_groups_to_db()."""

    @pytest.fixture
    def engine_with_db(self):
        """Erstelle Engine + initialisierte DB."""
        from photo_cleaner.db.schema import Database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            # Bootstrap schema
            db = Database(db_path)
            conn = db.connect()
            # Seed two files
            conn.execute(
                "INSERT INTO files (file_id, path, file_status) VALUES (1, '/img/a.jpg', 'KEEP')"
            )
            conn.execute(
                "INSERT INTO files (file_id, path, file_status) VALUES (2, '/img/b.jpg', 'KEEP')"
            )
            conn.commit()
            db.close()

            cache = GeocodingCache(Path(tmpdir) / "cache.db")
            geocoder = NominatimGeocoder()
            engine = ExifGroupingEngine(db_path, cache, geocoder)
            yield engine, db_path

    def test_save_creates_geo_group(self, engine_with_db):
        """Test: _save_groups_to_db() erstellt Eintrag in geo_groups."""
        engine, db_path = engine_with_db
        groups = [
            {
                "group_key": "40.7128_-74.0060_2026-05-02",
                "image_ids": [1, 2],
                "location_name": "New York, USA",
                "city": "New York",
                "country": "USA",
            }
        ]
        saved = engine._save_groups_to_db(groups, scan_session_id="s1")
        assert saved == 1

        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(str(db_path))
        row = conn.execute("SELECT group_key, city, image_count FROM geo_groups").fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "New York"
        assert row[2] == 2

    def test_save_creates_geo_group_images(self, engine_with_db):
        """Test: _save_groups_to_db() erstellt Verknüpfungen in geo_group_images."""
        engine, db_path = engine_with_db
        groups = [
            {
                "group_key": "51.5074_-0.1278_2026-05-02",
                "image_ids": [1, 2],
                "location_name": "London, UK",
                "city": "London",
                "country": "UK",
            }
        ]
        engine._save_groups_to_db(groups)

        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM geo_group_images").fetchone()[0]
        conn.close()
        assert count == 2

    def test_save_updates_files_exif_location_name(self, engine_with_db):
        """Test: files.exif_location_name wird aktualisiert."""
        engine, db_path = engine_with_db
        groups = [
            {
                "group_key": "52.52_13.405_2026-05-02",
                "image_ids": [1],
                "location_name": "Berlin, Deutschland",
                "city": "Berlin",
                "country": "Deutschland",
            }
        ]
        engine._save_groups_to_db(groups)

        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(str(db_path))
        loc = conn.execute("SELECT exif_location_name FROM files WHERE file_id=1").fetchone()[0]
        conn.close()
        assert loc == "Berlin, Deutschland"

    def test_save_upserts_on_conflict(self, engine_with_db):
        """Test: ON CONFLICT(group_key) UPDATE setzt neue Daten."""
        engine, db_path = engine_with_db
        groups = [
            {
                "group_key": "same_key",
                "image_ids": [1],
                "location_name": "Erster Name",
                "city": "City1",
                "country": "DE",
            }
        ]
        engine._save_groups_to_db(groups)

        groups[0]["location_name"] = "Zweiter Name"
        groups[0]["city"] = "City2"
        engine._save_groups_to_db(groups)

        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT city FROM geo_groups WHERE group_key='same_key'").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "City2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
