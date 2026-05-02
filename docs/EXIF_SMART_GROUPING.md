# EXIF Smart Grouping: Implementierungshandbuch

**Datum:** Mai 2026  
**Version:** 1.0.0-draft  
**Sprache:** Deutsch  
**Zielplattform:** Windows 10/11  
**Tech-Stack:** PySide6, Python 3.10+, SQLite, requests, OSM Nominatim

---

## Inhaltsverzeichnis

1. [Architekturübersicht](#1-architekturübersicht)
2. [Designentscheidungen](#2-designentscheidungen)
3. [Komponenten & Klassen](#3-komponenten--klassen)
4. [Datenbank-Schema](#4-datenbank-schema)
5. [Code-Beispiele](#5-code-beispiele)
6. [Integration in Bestehende Infrastruktur](#6-integration-in-bestehende-infrastruktur)
7. [Testplan](#7-testplan)
8. [Troubleshooting & Windows-Spezifika](#8-troubleshooting--windows-spezifika)
9. [Deployment & Rollout](#9-deployment--rollout)

---

## 1. Architekturübersicht

### 1.1 Komponenten-Diagramm

```
┌─────────────────────────────────────────────────────────────────┐
│              RatingWorkerThread (existierend)                    │
│              [Extrahiert EXIF: GPS, DateTimeOriginal]             │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ├─→ ExifGroupingEngine (neu)
               │   ├─→ Extrahiere GPS + Datum
               │   ├─→ Gruppiere nach Ort + Zeitstempel
               │   └─→ Speichere Gruppen in DB
               │
               ├─→ GeocodingCache (neu)
               │   ├─→ SQLite Cache-Tabelle
               │   ├─→ Memory-LRU Cache
               │   └─→ TTL-Verwaltung (7 Tage default)
               │
               ├─→ NominatimGeocoder (neu)
               │   ├─→ Reverse Geocoding (lat, lon → Ort)
               │   ├─→ Rate-Limiting (1 req/sec)
               │   └─→ Error-Handling + Retries
               │
               ├─→ GeolocationFallback (neu)
               │   ├─→ Tier 1: GPS-Koordinaten
               │   ├─→ Tier 2: Kamera-Ort-Metadaten
               │   ├─→ Tier 3: Zeitstempel-Clustering
               │   └─→ Tier 4: Ungrouped
               │
               └─→ GeovisualizationWidget (optional)
                   ├─→ Qt-WebView + Leaflet.js
                   ├─→ Interaktive Karte
                   └─→ Cluster-Visualization
```

### 1.2 Datenfluss: Von EXIF zur Gruppe

```
1. RatingWorkerThread finisht
   └─→ EXIF extrahiert: GPS (lat, lon), DateTimeOriginal

2. ExifGroupingEngine startet
   ├─→ Gruppiere: (lat, lon) + Date
   └─→ Pro Gruppe: Erstelle GeoGroup-Objekt

3. Für jede GeoGroup: Reverse Geocoding
   ├─→ GeocodingCache prüfen
   ├─→ Falls gefunden: Verwende cached Ort
   └─→ Falls nicht: NominatimGeocoder → API-Call

4. Fallback-Kette bei fehlenden GPS-Daten
   ├─→ Tier 1: GPS verfügbar? → Nutze Geocoding
   ├─→ Tier 2: Camera-Ort-Metadaten? → "Canon EOS R6 Locations"
   ├─→ Tier 3: Zeitstempel-Cluster? → "2026-05-02"
   └─→ Tier 4: Ungrouped → "Ohne Ort-Info"

5. Speichere Gruppen in DB
   ├─→ geo_groups Tabelle
   ├─→ geo_group_images Verknüpfung
   └─→ Aktualisiere Image-EXIF-Daten

6. UI zeigt Gruppen an
   ├─→ Gallery: Filter nach Gruppe
   ├─→ Map: Interaktive Visualisierung (optional)
   └─→ Statistik: "X Gruppen, Y Orte"
```

---

## 2. Designentscheidungen

### 2.1 Warum OSM Nominatim?

**Gewählt: Nominatim (kostenlos, self-hosted möglich)**

**Vergleich:**
| Kriterium | Nominatim | Google Maps | HERE | Bing |
|-----------|-----------|------------|------|------|
| Kosten | Kostenlos | $7 pro 1k | $1+ pro 1k | kostenpflichtig |
| API-Keys | Keine | Erforderlich | Erforderlich | Erforderlich |
| Privacy | 100% lokal | Google-Daten | Kommerziell | Kommerziell |
| Offline | Self-Host möglich | Nein | Nein | Nein |
| Rate-Limit | 1 req/sec | 25k/24h | Custom | Custom |

**Fallback-Strategie:**
- Primary: `nominatim.openstreetmap.org` (public, kostenlos)
- Fallback: Self-hosted Nominatim (falls vorhanden)
- Offline: Cache + Local GeoNames DB (optional)

### 2.2 Caching-Strategie

**Hybrid Caching: Memory + SQLite**

```python
# Memory-Cache (LRU, 1000 entries max)
(40.7128, -74.0060) → {"city": "New York", "country": "USA", "cached_at": "2026-05-02"}

# SQLite Persistent Cache
CREATE TABLE geocoding_cache (
    coordinates TEXT PRIMARY KEY,  -- "40.7128,-74.0060"
    location_name TEXT,
    city TEXT,
    country TEXT,
    cached_at TIMESTAMP,
    ttl_hours INT DEFAULT 168  -- 7 days
)
```

**TTL-Verwaltung:**
- Neue Einträge: 168 Stunden (7 Tage)
- Alte Einträge: Auto-Cleanup nach TTL-Ablauf
- Manuelle Clear: Settings → Cache leeren

### 2.3 Fallback-Hierarchie

**4-Tier-System bei fehlenden GPS-Daten:**

```
Tier 1: GPS vorhanden
├─→ Reverse Geocoding via Nominatim
├─→ Ort-Name: "Munich, Germany"
└─→ Datumsbereich: "2026-04-15 bis 2026-04-20"

Tier 2: GPS fehlt, Kamera-Ort vorhanden
├─→ EXIF MakerNote oder ExifIFD ort-Metadaten
├─→ Fallback: "Canon EOS R6 Locations" (Kamera-Standorte)
└─→ Gruppe: Nach Datum clustern

Tier 3: GPS + Kamera-Ort fehlt, Zeitstempel vorhanden
├─→ Gruppiere nur nach Datum
├─→ Gruppe: "2026-05-02"
└─→ "Ohne Ort-Info, aber vom selben Tag"

Tier 4: Nichts vorhanden
├─→ Gruppe: "Ungrouped"
└─→ "Keine EXIF-Metadaten"
```

### 2.4 FREE-Lizenz Integration

**Logik:**
- EXIF-Grouping läuft auch für FREE-Bilder (kostet nichts zusätzlich)
- Geocoding-Cache ist SHARED (zwischen Scans)
- API-Calls zählen NICHT gegen 250er-Limit
- Optional: PRO könnte erweiterte Geocoding-Features haben (z.B. reverse-search, place-search)

---

## 3. Komponenten & Klassen

### 3.1 `ExifGroupingEngine` (Orchestrierung)

**Datei:** `src/photo_cleaner/exif/grouping_engine.py`

**Verantwortung:**
- Extrahiere EXIF-Metadaten (GPS, Datum)
- Erstelle geografische + zeitliche Gruppen
- Triggere Geocoding
- Speichere Gruppen in DB

### 3.2 `NominatimGeocoder` (Reverse Geocoding)

**Datei:** `src/photo_cleaner/exif/nominatim_geocoder.py`

**Verantwortung:**
- Rufe Nominatim API auf
- Rate-Limiting (1 req/sec)
- Error-Handling + Retries
- User-Agent Management

### 3.3 `GeocodingCache` (Hybrid Caching)

**Datei:** `src/photo_cleaner/exif/geocoding_cache.py`

**Verantwortung:**
- Memory-LRU Cache für Hot-Data
- SQLite Persistent Cache
- TTL-Management
- Cache-Statistiken

### 3.4 `GeolocationFallback` (Robustheit)

**Datei:** `src/photo_cleaner/exif/geolocation_fallback.py`

**Verantwortung:**
- 4-Tier Fallback-Logik
- Alternative Ort-Quellen
- Zeitstempel-Clustering
- Fehlertoleranz

---

## 4. Datenbank-Schema

### 4.1 Neue Tabellen

```sql
-- Geografische Gruppen
CREATE TABLE geo_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_session_id TEXT,           -- FK zu scan_sessions
    group_key TEXT NOT NULL UNIQUE, -- "40.7128,-74.0060_2026-05-02"
    latitude REAL,
    longitude REAL,
    location_name TEXT,             -- "New York, USA" (cached)
    city TEXT,
    country TEXT,
    date_start DATE,                -- "2026-05-02"
    date_end DATE,                  -- "2026-05-07"
    image_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Mapping: Bilder ↔ Gruppen
CREATE TABLE geo_group_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    geo_group_id INTEGER NOT NULL,
    image_id INTEGER NOT NULL,
    FOREIGN KEY (geo_group_id) REFERENCES geo_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
    UNIQUE(geo_group_id, image_id)
);

-- Nominatim Caching
CREATE TABLE geocoding_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coordinates TEXT NOT NULL UNIQUE, -- "40.7128,-74.0060"
    location_name TEXT,
    city TEXT,
    country TEXT,
    raw_response TEXT,                -- JSON für Debugging
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ttl_hours INTEGER DEFAULT 168,    -- 7 days
    hits INTEGER DEFAULT 0            -- Cache-Hit Counter
);

-- Fallback-Tracking (optional, für Stats)
CREATE TABLE grouping_fallback_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    tier_used INTEGER,                -- 1=GPS, 2=Camera, 3=Date, 4=Ungrouped
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Erweiterung bestehender Tabellen

```sql
-- Neue Spalten in images-Tabelle
ALTER TABLE images ADD COLUMN geo_group_id INTEGER;
ALTER TABLE images ADD COLUMN exif_latitude REAL;
ALTER TABLE images ADD COLUMN exif_longitude REAL;
ALTER TABLE images ADD COLUMN exif_location_name TEXT;
ALTER TABLE images ADD COLUMN exif_date_original TEXT;
ALTER TABLE images ADD COLUMN exif_camera_location TEXT;
```

---

## 5. Code-Beispiele

### 5.1 `ExifGroupingEngine` - Skeleton

```python
"""
ExifGroupingEngine: Orchestriert Gruppierung nach Ort + Datum.
"""

import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from PySide6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ExifGroupingEngine(QObject):
    """Extrahiert EXIF-Metadaten und erstellt geografische Gruppen."""
    
    # Signale
    grouping_started = pyqtSignal(int)  # count: int
    grouping_progress = pyqtSignal(int, int)  # current, total
    grouping_completed = pyqtSignal(dict)  # result_summary
    grouping_error = pyqtSignal(str)  # error_message
    
    def __init__(self, db_path: Path, geocoding_cache, geocoder):
        """
        Initialisiert die Engine.
        
        Args:
            db_path: Path zur SQLite DB
            geocoding_cache: GeocodingCache-Instanz
            geocoder: NominatimGeocoder-Instanz
        """
        super().__init__()
        self.db_path = db_path
        self.geocoding_cache = geocoding_cache
        self.geocoder = geocoder
        self._is_running = False
    
    def group_images(self, image_list: list, scan_session_id: str = None):
        """
        Gruppiert Bilder nach Ort + Datum.
        
        Args:
            image_list: Liste von Image-Objekten mit EXIF-Daten
            scan_session_id: Optional, für DB-Verknüpfung
        """
        if self._is_running:
            logger.warning("ExifGroupingEngine: Grouping läuft bereits")
            return
        
        self._is_running = True
        self.grouping_started.emit(len(image_list))
        
        try:
            # 1. Extrahiere EXIF-Metadaten
            exif_data = self._extract_exif_data(image_list)
            
            # 2. Erstelle Gruppen
            groups = self._create_groups(exif_data)
            
            # 3. Reverse Geocoding für jede Gruppe
            for group in groups:
                self._geocode_group(group)
                self.grouping_progress.emit(
                    groups.index(group), len(groups)
                )
            
            # 4. Speichere in DB
            saved_count = self._save_groups_to_db(groups, scan_session_id)
            
            result = {
                "total_images": len(image_list),
                "groups_created": len(groups),
                "groups_saved": saved_count,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"ExifGroupingEngine: Grouping abgeschlossen. "
                       f"{result['total_images']} Bilder in {result['groups_created']} Gruppen")
            self.grouping_completed.emit(result)
        
        except Exception as e:
            logger.error(f"ExifGroupingEngine: Fehler: {e}", exc_info=True)
            self.grouping_error.emit(str(e))
        
        finally:
            self._is_running = False
    
    def _extract_exif_data(self, image_list: list) -> dict:
        """Extrahiere EXIF-Daten aus Bildern."""
        exif_data = {}
        
        for image in image_list:
            # [FILL: Integration mit existierendem EXIF-Extractor]
            # Erwartete Struktur:
            # {
            #     "image_id": "...",
            #     "latitude": 40.7128,
            #     "longitude": -74.0060,
            #     "date_original": "2026-05-02",
            #     "camera_model": "Canon EOS R6"
            # }
            pass
        
        return exif_data
    
    def _create_groups(self, exif_data: dict) -> list:
        """Erstelle Gruppen nach (lat, lon) + Date."""
        groups_dict = defaultdict(list)
        
        for image_id, exif in exif_data.items():
            # Erstelle Group-Key
            lat = exif.get('latitude')
            lon = exif.get('longitude')
            date = exif.get('date_original', '1970-01-01')
            
            # Fallback: Falls GPS fehlt
            if lat is None or lon is None:
                group_key = f"no_gps_{date}"
            else:
                group_key = f"{lat:.4f}_{lon:.4f}_{date}"
            
            groups_dict[group_key].append(image_id)
        
        # Konvertiere zu GeoGroup-Objekten
        groups = [
            {
                "group_key": key,
                "image_ids": ids,
                "count": len(ids)
            }
            for key, ids in groups_dict.items()
        ]
        
        logger.info(f"ExifGroupingEngine: {len(groups)} Gruppen erstellt")
        return groups
    
    def _geocode_group(self, group: dict):
        """Reverse Geocoding für eine Gruppe."""
        group_key = group["group_key"]
        
        if group_key.startswith("no_gps"):
            # Fallback: Keine GPS-Daten
            group["location_name"] = "Ohne Ort-Info"
            return
        
        # Extrahiere lat/lon aus group_key
        parts = group_key.split("_")
        try:
            lat, lon = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            group["location_name"] = "Ungültige Koordinaten"
            return
        
        # Versuche zu geocoden
        location = self.geocoding_cache.get((lat, lon))
        
        if location is None:
            # API-Call
            location = self.geocoder.reverse_geocode(lat, lon)
            if location:
                self.geocoding_cache.set((lat, lon), location)
        
        group["location_name"] = location.get("city", "Unknown") if location else "Fehler"
    
    def _save_groups_to_db(self, groups: list, scan_session_id: str = None) -> int:
        """Speichere Gruppen in DB."""
        # [FILL: DB-Integration]
        logger.debug(f"ExifGroupingEngine: Speichere {len(groups)} Gruppen")
        return len(groups)
```

### 5.2 `NominatimGeocoder` - Skeleton

```python
"""
NominatimGeocoder: Reverse Geocoding via OSM Nominatim.
"""

import logging
import time
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class NominatimGeocoder:
    """Reverse Geocoding using OpenStreetMap Nominatim."""
    
    # API Config
    BASE_URL = "https://nominatim.openstreetmap.org/reverse"
    RATE_LIMIT_DELAY = 1.0  # 1 request per second (per ToS)
    TIMEOUT = 10
    MAX_RETRIES = 3
    
    def __init__(self, user_agent: str = "PhotoCleaner/0.8.7"):
        """
        Initialisiert den Geocoder.
        
        Args:
            user_agent: User-Agent Header (Nominatim requires this)
        """
        self.user_agent = user_agent
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
    
    def reverse_geocode(self, latitude: float, longitude: float) -> dict:
        """
        Reverse Geocoding: Koordinaten → Ort-Name.
        
        Args:
            latitude: Breite
            longitude: Länge
        
        Returns:
            Dict: {"city": "...", "country": "...", "address": {...}}
            oder None bei Fehler
        """
        # Rate-Limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - time_since_last)
        
        params = {
            "format": "json",
            "lat": latitude,
            "lon": longitude,
            "zoom": 10,
            "addressdetails": 1
        }
        
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(f"Nominatim: Reverse-Geocode ({latitude:.4f}, {longitude:.4f})")
                
                response = self.session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.TIMEOUT
                )
                
                self.last_request_time = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "city": data.get("address", {}).get("city", "Unknown"),
                        "country": data.get("address", {}).get("country", "Unknown"),
                        "address": data.get("address", {}),
                        "display_name": data.get("display_name", ""),
                        "cached_at": datetime.now().isoformat()
                    }
                elif response.status_code == 429:
                    # Rate-Limited
                    logger.warning(f"Nominatim: Rate-Limited (429), retry {attempt}")
                    time.sleep(5 * (attempt + 1))
                else:
                    logger.warning(f"Nominatim: HTTP {response.status_code}")
                    return None
            
            except requests.Timeout:
                logger.warning(f"Nominatim: Timeout (attempt {attempt})")
            except requests.ConnectionError:
                logger.warning(f"Nominatim: Connection Error (attempt {attempt})")
            except Exception as e:
                logger.error(f"Nominatim: Fehler: {e}")
                return None
        
        return None
```

### 5.3 `GeocodingCache` - Skeleton

```python
"""
GeocodingCache: Hybrid Memory + SQLite Caching für Reverse-Geocoding.
"""

import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger(__name__)


class GeocodingCache:
    """Hybrid Memory (LRU) + SQLite Persistent Cache."""
    
    def __init__(self, db_path: Path, max_memory_entries: int = 1000, ttl_days: int = 7):
        """
        Initialisiert den Cache.
        
        Args:
            db_path: Path zur Cache-DB
            max_memory_entries: LRU Memory-Cache Max-Einträge
            ttl_days: Time-to-Live für Cache-Einträge (Tage)
        """
        self.db_path = db_path
        self.max_memory_entries = max_memory_entries
        self.ttl_days = ttl_days
        
        # Memory-LRU Cache
        self.memory_cache = OrderedDict()
        
        # Setup DB
        self._init_db()
        self._cleanup_expired()
    
    def get(self, coordinates: tuple) -> dict:
        """
        Hole Geocoding-Ergebnis aus Cache.
        
        Args:
            coordinates: (latitude, longitude) tuple
        
        Returns:
            Dict oder None
        """
        # 1. Memory-Cache prüfen
        if coordinates in self.memory_cache:
            logger.debug(f"GeocodingCache: Memory hit for {coordinates}")
            # Move to end (LRU)
            self.memory_cache.move_to_end(coordinates)
            return self.memory_cache[coordinates]
        
        # 2. DB-Cache prüfen
        result = self._get_from_db(coordinates)
        if result:
            logger.debug(f"GeocodingCache: DB hit for {coordinates}")
            # Add to memory-cache
            self._add_to_memory(coordinates, result)
            return result
        
        logger.debug(f"GeocodingCache: Cache miss for {coordinates}")
        return None
    
    def set(self, coordinates: tuple, location_data: dict):
        """
        Speichere Geocoding-Ergebnis im Cache.
        
        Args:
            coordinates: (latitude, longitude) tuple
            location_data: Dict mit city, country, etc.
        """
        # Memory-Cache
        self._add_to_memory(coordinates, location_data)
        
        # DB-Cache
        self._save_to_db(coordinates, location_data)
    
    def _add_to_memory(self, coordinates: tuple, data: dict):
        """Add to Memory-LRU, evict oldest if over limit."""
        self.memory_cache[coordinates] = data
        self.memory_cache.move_to_end(coordinates)
        
        if len(self.memory_cache) > self.max_memory_entries:
            # Remove oldest (FIFO)
            self.memory_cache.popitem(last=False)
    
    def _init_db(self):
        """Initialize SQLite Cache-Tabelle."""
        # [FILL: DB-Schema aus Abschnitt 4.1]
        pass
    
    def _get_from_db(self, coordinates: tuple) -> dict:
        """Hole Eintrag aus SQLite Cache."""
        # [FILL: SQL SELECT]
        pass
    
    def _save_to_db(self, coordinates: tuple, location_data: dict):
        """Speichere Eintrag in SQLite Cache."""
        # [FILL: SQL INSERT/UPDATE]
        pass
    
    def _cleanup_expired(self):
        """Lösche abgelaufene Cache-Einträge."""
        # [FILL: DELETE WHERE cached_at < now() - ttl_hours]
        logger.info("GeocodingCache: Cleanup expired entries")
    
    def clear_all(self):
        """Leere gesamten Cache (Memory + DB)."""
        self.memory_cache.clear()
        # [FILL: DELETE FROM geocoding_cache]
        logger.info("GeocodingCache: Vollständig geleert")
    
    def get_statistics(self) -> dict:
        """Gebe Cache-Statistiken zurück."""
        return {
            "memory_entries": len(self.memory_cache),
            "db_entries": 0,  # [FILL: COUNT FROM geocoding_cache]
            "ttl_days": self.ttl_days
        }
```

---

## 6. Integration in Bestehende Infrastruktur

### 6.1 Mit RatingWorkerThread

Nach `RatingWorkerThread.run()` abgeschlossen:

```python
# In modern_window.py nach RatingWorkerThread-Completion

self._exif_grouping_engine.group_images(
    image_list=analyzed_images,
    scan_session_id=self.current_scan_session_id
)
```

### 6.2 Mit UI (GalleryView)

```python
# In GalleryView oder ähnlich

# Filter-Dropdown für Gruppen
def _populate_group_filter(self):
    """Populate location grouping filter."""
    from photo_cleaner.db import get_db_manager
    
    db = get_db_manager()
    groups = db.get_all_geo_groups()
    
    for group in groups:
        self.group_filter_combo.addItem(
            group["location_name"],
            userData=group["id"]
        )
```

### 6.3 Mit AppConfig

```python
# In config.py

class AppConfig:
    def __init__(self, ...):
        # ... existing ...
        
        # EXIF Grouping
        self.exif_grouping_enabled = self.get('exif.grouping_enabled', True)
        self.geocoding_cache_ttl_days = self.get('exif.geocoding_cache_ttl_days', 7)
        self.nominatim_base_url = self.get('exif.nominatim_url', 
                                          'https://nominatim.openstreetmap.org/reverse')
```

---

## 7. Testplan

### 7.1 Unit-Tests

```python
# tests/test_exif_grouping.py

class TestNominatimGeocoder:
    def test_reverse_geocode_valid_coordinates(self):
        """Test: Valide Koordinaten werden korrekt geocoded."""
        geocoder = NominatimGeocoder()
        result = geocoder.reverse_geocode(40.7128, -74.0060)
        assert result is not None
        assert "city" in result
        assert "New York" in result.get("city", "")
    
    def test_rate_limiting(self):
        """Test: Rate-Limiting wird eingehalten."""
        geocoder = NominatimGeocoder()
        import time
        start = time.time()
        geocoder.reverse_geocode(40.7128, -74.0060)
        geocoder.reverse_geocode(51.5074, -0.1278)
        elapsed = time.time() - start
        assert elapsed >= 1.0  # Min. 1 sec zwischen Requests

class TestGeocodingCache:
    def test_memory_cache_hit(self):
        """Test: Memory-Cache wird getroffen."""
        cache = GeocodingCache(...)
        cache.set((40.7128, -74.0060), {"city": "New York"})
        result = cache.get((40.7128, -74.0060))
        assert result["city"] == "New York"
    
    def test_lru_eviction(self):
        """Test: LRU Eviction bei Max-Einträgen."""
        cache = GeocodingCache(..., max_memory_entries=2)
        cache.set((1, 1), {"city": "A"})
        cache.set((2, 2), {"city": "B"})
        cache.set((3, 3), {"city": "C"})  # Sollte (1,1) evicten
        assert cache.get((1, 1)) is None
        assert cache.get((3, 3)) is not None

class TestExifGroupingEngine:
    def test_group_images_by_location_date(self):
        """Test: Bilder werden nach Ort + Datum gruppiert."""
        engine = ExifGroupingEngine(...)
        images = [...]  # Mock Images mit EXIF
        engine.group_images(images)
        # Verify: Groups erstellt, Geocoding aufgerufen
```

### 7.2 E2E-Tests

```
1. EXIF-Extraktion → Grouping → DB-Speicherung
2. API-Fehler-Szenarien (Timeout, Rate-Limit)
3. Fallback-Ketten (GPS → Datum → Ungrouped)
4. Cache-Persistierung (Restart → Cache geladen)
5. UI-Integration (Filter, Visualisierung)
```

---

## 8. Troubleshooting & Windows-Spezifika

### 8.1 Nominatim API-Fehler

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| **429 Rate Limited** | Zu viele Requests | Erhöhe RATE_LIMIT_DELAY auf 2s |
| **Timeout** | Langsame Verbindung | Erhöhe TIMEOUT auf 15s, retry |
| **404 Not Found** | Koordinaten ungültig | Prüfe GPS-Daten auf Plausibilität |
| **Proxy-Fehler** | Firewall blockiert | Nutze Proxy-Settings oder Fallback-URL |

### 8.2 Cache-Verwaltung

```
Ort: %APPDATA%\PhotoCleaner\geocoding_cache.db
Größe: ~10 MB pro 10.000 Einträge
Cleanup: Automatisch nach 7 Tagen (TTL)
Manuell: Settings → Cache leeren
```

### 8.3 Performance-Optimierung

- **Batch-Geocoding:** Max 100 neue Koordinaten pro Scan
- **Caching-Strategie:** 99% Hit-Rate erwartet nach 2. Scan
- **Offlinebetrieb:** Cache reicht für offline-Zugriff

---

## 9. Deployment & Rollout

### 9.1 Implementierungs-Roadmap

```
Woche 1:
  - [ ] DB-Schema + Migrationen
  - [ ] NominatimGeocoder + GeocodingCache
  - [ ] Unit-Tests (60%)

Woche 2:
  - [ ] ExifGroupingEngine vollständig
  - [ ] Integration in RatingWorkerThread
  - [ ] E2E-Tests
  - [ ] UI-Integration (Filter/Dropdown)
  - [ ] Performance-Optimization
```

### 9.2 Rollout-Strategie

**Alpha (Private):**
- Nur Entwickler
- Feedback: API-Zuverlässigkeit, Cache-Größe

**Beta (10 Tester):**
- verschiedene Kamera-Typen
- Verschiedene Netzwerk-Szenarien (VPN, Proxy, Offline)
- Verschiedene Bild-Mengen (10 bis 500 Bilder)

**RC (Public):**
- Feature-Freeze
- Nur Bug-Fixes

---

**Ende des Dokuments**

*EXIF Smart Grouping ist eine Erweiterung der bestehenden Analyse-Pipeline. Alle neuen Komponenten sind optional und verzögern bestehende Workflows nicht.*
