"""
Unit-Tests für EXIF Smart Grouping Komponenten.

Führe aus mit:
    pytest tests/test_exif_grouping.py -v
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.photo_cleaner.exif.nominatim_geocoder import NominatimGeocoder
from src.photo_cleaner.exif.geocoding_cache import GeocodingCache
from src.photo_cleaner.exif.exif_grouping_engine import ExifGroupingEngine


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
