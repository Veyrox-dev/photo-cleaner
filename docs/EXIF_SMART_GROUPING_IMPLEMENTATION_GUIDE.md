# EXIF Smart Grouping: Implementierungs-Leitfaden

**Zielgruppe:** Entwickler  
**Komplexität:** Mittel  
**Geschätzter Aufwand:** 2-3 Tage für Full Integration + Testing  

---

## Quick Start

### 1. Komponenten sind bereit!

```
src/photo_cleaner/exif/
├── __init__.py                      ✅ Paket-Einstiegspunkt
├── nominatim_geocoder.py            ✅ Reverse Geocoding (100% complete)
├── geocoding_cache.py               ✅ Hybrid Caching (100% complete)
└── exif_grouping_engine.py          ⏳ Placeholder für EXIF-Extraktion & DB-Integration
```

### 2. Nächste Schritte (in dieser Reihenfolge)

```
Phase 1: DB-SCHEMA (1 Tag)
  ├─ [ ] Migrationsskript erstellen (4 neue Tabellen)
  ├─ [ ] Tests für Tabellen-Struktur
  └─ [ ] Validierung auf Test-DB

Phase 2: EXIF-INTEGRATION (1 Tag)
  ├─ [ ] _extract_exif_data() implementieren (FILL: RatingWorkerThread Integration)
  ├─ [ ] _save_groups_to_db() implementieren (FILL: SQL INSERT)
  └─ [ ] DB-Migrationen testen

Phase 3: TESTING & INTEGRATION (1 Tag)
  ├─ [ ] Unit-Tests (pytest tests/test_exif_grouping.py)
  ├─ [ ] E2E-Tests (EXIF → Grouping → Gallery anzeigen)
  └─ [ ] Performance: 250 Bilder sollten <5s Grouping dauern

Phase 4: UI-INTEGRATION (optional, 1 Tag)
  ├─ [ ] Gallery-Filter nach Location
  ├─ [ ] Gruppen-Statistik anzeigen
  └─ [ ] Map-Visualisierung (optional, Leaflet)
```

---

## Phase 1: DB-Schema Implementierung

### 1.1 Migrations-Datei erstellen

**Datei:** `src/photo_cleaner/db/migrations/0004_add_geolocation.sql`

```sql
-- Migration: Add Geolocation Grouping Tables
-- Version: 0004
-- Description: Neue Tabellen für EXIF Smart Grouping (Ort + Datum)

-- Geografische Gruppen
CREATE TABLE geo_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_session_id TEXT,
    group_key TEXT NOT NULL UNIQUE,
    latitude REAL,
    longitude REAL,
    location_name TEXT,
    city TEXT,
    country TEXT,
    date_start DATE,
    date_end DATE,
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

-- Nominatim Caching (wird im Python-Code verwaltet, in geo DB)
CREATE TABLE geocoding_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coordinates TEXT NOT NULL UNIQUE,
    location_name TEXT,
    city TEXT,
    country TEXT,
    raw_response TEXT,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ttl_hours INTEGER DEFAULT 168,
    hits INTEGER DEFAULT 0
);

-- Fallback-Tracking
CREATE TABLE grouping_fallback_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    tier_used INTEGER,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_geo_groups_location ON geo_groups(location_name);
CREATE INDEX idx_geo_groups_session ON geo_groups(scan_session_id);
CREATE INDEX idx_geo_group_images_group ON geo_group_images(geo_group_id);
CREATE INDEX idx_geo_group_images_image ON geo_group_images(image_id);
CREATE INDEX idx_geocoding_coordinates ON geocoding_cache(coordinates);

-- Erweiterung existierende images-Tabelle
ALTER TABLE images ADD COLUMN geo_group_id INTEGER;
ALTER TABLE images ADD COLUMN exif_latitude REAL;
ALTER TABLE images ADD COLUMN exif_longitude REAL;
ALTER TABLE images ADD COLUMN exif_location_name TEXT;
ALTER TABLE images ADD COLUMN exif_date_original TEXT;
ALTER TABLE images ADD COLUMN exif_camera_location TEXT;
```

### 1.2 DB-Manager erweitern

**Datei:** `src/photo_cleaner/db/db_manager.py` (neue Methoden hinzufügen)

```python
class DatabaseManager:
    # ... existing ...
    
    def create_geo_group(self, group_key: str, location_name: str, 
                        latitude: float = None, longitude: float = None) -> int:
        """Erstelle neue geografische Gruppe."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO geo_groups 
            (group_key, location_name, latitude, longitude, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (group_key, location_name, latitude, longitude, datetime.now().isoformat()))
        self.conn.commit()
        return cursor.lastrowid
    
    def add_image_to_geo_group(self, geo_group_id: int, image_id: int):
        """Verknüpfe Bild mit geografischer Gruppe."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO geo_group_images (geo_group_id, image_id)
            VALUES (?, ?)
        """, (geo_group_id, image_id))
        self.conn.commit()
    
    def get_all_geo_groups(self) -> list:
        """Gebe alle geografischen Gruppen zurück."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, group_key, location_name, city, country, 
                   COUNT(gi.id) as image_count
            FROM geo_groups g
            LEFT JOIN geo_group_images gi ON g.id = gi.geo_group_id
            GROUP BY g.id
            ORDER BY location_name
        """)
        return cursor.fetchall()
```

---

## Phase 2: EXIF-Integration

### 2.1 `_extract_exif_data()` implementieren

In `exif_grouping_engine.py`, ersetze Placeholder:

```python
def _extract_exif_data(self, image_list: List) -> Dict:
    """Extrahiere EXIF-Daten aus Bildern."""
    from photo_cleaner.analysis.rating_worker import RatingWorkerThread
    
    exif_data = {}
    
    for image in image_list:
        try:
            # Annahme: image.exif_metadata bereits durch RatingWorkerThread gefüllt
            exif = {
                "image_id": image.id,
                "latitude": image.exif_metadata.get("latitude"),
                "longitude": image.exif_metadata.get("longitude"),
                "date_original": image.exif_metadata.get("date_original"),
                "camera_model": image.exif_metadata.get("camera_model")
            }
            exif_data[image.id] = exif
        except Exception as e:
            logger.warning(f"Fehler beim EXIF-Lesen: {e}")
            continue
    
    return exif_data
```

### 2.2 `_save_groups_to_db()` implementieren

```python
def _save_groups_to_db(self, groups: List[Dict], 
                       scan_session_id: Optional[str] = None) -> int:
    """Speichere Gruppen in DB."""
    from photo_cleaner.db import get_db_manager
    
    db = get_db_manager()
    saved = 0
    
    try:
        for group in groups:
            # Erstelle Gruppe
            geo_group_id = db.create_geo_group(
                group_key=group["group_key"],
                location_name=group.get("location_name", "Unknown"),
                latitude=float(group["group_key"].split("_")[0]) if "_" in group["group_key"] else None,
                longitude=float(group["group_key"].split("_")[1]) if "_" in group["group_key"] else None
            )
            
            # Verknüpfe Bilder
            for image_id in group["image_ids"]:
                db.add_image_to_geo_group(geo_group_id, image_id)
            
            saved += 1
        
        logger.info(f"ExifGroupingEngine: {saved} Gruppen in DB gespeichert")
        return saved
    
    except Exception as e:
        logger.error(f"ExifGroupingEngine: Fehler beim DB-Speichern: {e}", exc_info=True)
        return 0
```

---

## Phase 3: Integration in modern_window.py

### 3.1 Import hinzufügen

```python
from photo_cleaner.exif.exif_grouping_engine import ExifGroupingEngine
from photo_cleaner.exif.geocoding_cache import GeocodingCache
from photo_cleaner.exif.nominatim_geocoder import NominatimGeocoder
```

### 3.2 In `__init__()` initialisieren

```python
# Nach RatingWorkerThread Initialisierung

self._geocoding_cache = GeocodingCache(
    db_path=self.app_config.cache_dir / "geocoding_cache.db",
    ttl_days=7
)
self._nominatim_geocoder = NominatimGeocoder()
self._exif_grouping_engine = ExifGroupingEngine(
    db_path=self.db_manager.db_path,
    geocoding_cache=self._geocoding_cache,
    geocoder=self._nominatim_geocoder
)

# Signale verbinden
self._exif_grouping_engine.grouping_completed.connect(self._on_grouping_completed)
```

### 3.3 Nach RatingWorkerThread triggern

```python
# In _on_rating_finished() oder ähnlich

if self._exif_grouping_engine:
    self._exif_grouping_engine.group_images(
        image_list=analyzed_images,
        scan_session_id=self.current_scan_session_id
    )

def _on_grouping_completed(self, result: dict):
    """Callback: EXIF Grouping abgeschlossen."""
    logger.info(f"EXIF Grouping: {result['groups_created']} Gruppen erstellt")
    # Optional: UI aktualisieren (Gallery-Filter, Map)
```

---

## Phase 4: Testing

### 4.1 Unit-Tests ausführen

```bash
pytest tests/test_exif_grouping.py -v
```

### 4.2 E2E-Test

**Szenario:** 
1. Lade 50 Bilder mit GPS-Metadaten
2. Starte Analyse
3. Prüfe: geo_groups Tabelle hat Einträge
4. Prüfe: geo_group_images hat Bilder-Zuordnungen
5. Prüfe: geocoding_cache hat Einträge

---

## Checkliste

- [ ] DB-Migrations-Skript ausführen
- [ ] DB-Manager neue Methoden testen
- [ ] `_extract_exif_data()` implementiert & getestet
- [ ] `_save_groups_to_db()` implementiert & getestet
- [ ] Integration in modern_window.py
- [ ] Unit-Tests grün
- [ ] E2E-Test erfolgreich
- [ ] Performance: <5s für 250 Bilder
- [ ] Geocoding-Cache funktioniert (DB + Memory)
- [ ] Nominatim Rate-Limiting funktioniert
- [ ] UI-Integration (optional)

---

**Los geht's! 🚀**
