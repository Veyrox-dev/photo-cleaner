# ImageCache System für PhotoCleaner
> Moved to [tech/CACHE_SYSTEM.md](tech/CACHE_SYSTEM.md).

## Übersicht

Das **ImageCache-System** ist eine optional persistente Caching-Schicht, die bereits bewertete Bilder erkennt und bei erneutem Scan eine teure Medienanalyse (inkl. MediaPipe/Scoring) vermeidet.

**Ziel**: Massive Reduktion der Rechenzeit bei großen Bildersammlungen durch Cache-Hits bei bereits analysierten Bildern.

**Performance-Impact**:
- Cache Hit: ~0.1s pro Bild (nur Datenbankabfrage)
- Cache Miss (MediaPipe): ~1-5s pro Bild (AnalyseNeue Bilder)
- **Zeitersparnis bei wiederholten Scans: 80-90%**

---

## Architektur

### 1. **ImageCacheManager** (Kernklasse)

Verwaltet persistente Speicherung und Abruf von Analyse-Ergebnissen.

```python
from photo_cleaner.cache import ImageCacheManager

# Initialisierung
cache = ImageCacheManager(db.conn)

# Lookup
entry = cache.lookup(file_path)  # CacheEntry oder None
if entry:
    quality_score = entry.quality_score
    top_n_flag = entry.top_n_flag

# Storage
cache.store(
    file_path=Path("img.jpg"),
    quality_score=85.5,
    top_n_flag=True,
    metadata={"faces_detected": 2}
)

# Bulk Lookup
uncached, cached = cache.bulk_lookup(file_paths_list)
```

### 2. **Datenstruktur (SQLite)**

```sql
CREATE TABLE image_cache (
    cache_id INTEGER PRIMARY KEY,
    image_hash TEXT UNIQUE,           -- SHA1 des Dateiiinhalts
    quality_score REAL,                -- Bewertungsscore (0-100)
    top_n_flag BOOLEAN,                -- Ist in Top-N für diese Gruppe
    analysis_timestamp REAL,           -- Wann analysiert
    pipeline_version INTEGER,          -- Cache-Format-Version
    metadata_json TEXT,                -- Optionale Metadaten (JSON)
    created_at REAL,
    updated_at REAL
);
```

### 3. **Pipeline-Integration**

Die Cache-Integration ist **minimal invasiv** und sitzt **vor der Quality-Analysis-Stage**:

```
Stage 3 (Cheap Filter) ✓
    ↓
Cache Check ← NEW
    ├─ Cache Hit  → Load Score + Top-N Flag → Skip to Scoring
    └─ Cache Miss → Continue to Quality Analysis
        ↓
Stage 4 (Quality Analysis) ✓ + Store in Cache
    ↓
Stage 5 (Scoring) ✓
```

### 4. **Hash-Berechnung**

Verwendet **SHA1-Hash des Dateiiinhalts** für eindeutige Identifikation:

```python
file_hash = ImageCacheManager.compute_file_hash(Path("img.jpg"))
# SHA1: "3e4a8f7c...d2b9e1a" (40 Zeichen)
```

**Vorteil**: Identifiziert dieselbe Datei über Speicherorte hinweg.

**Trade-off**: ~100ms pro Datei (einmalig), aber zuverlässigere Identifikation als Pfad.

---

## Verwendung

### A. **Automatische Caching in Pipeline**

Wenn `use_cache=True` (Standard):

```python
from photo_cleaner.pipeline.pipeline import PhotoCleanerPipeline, PipelineConfig

config = PipelineConfig(
    use_cache=True,              # Enable caching
    force_reanalyze=False,       # Use cache if available
)
pipeline = PhotoCleanerPipeline(db, config)
stats = pipeline.run(folder_path)

# Stats beinhalten jetzt:
print(f"Cache hits: {stats.cache_hits}")
print(f"Cache misses: {stats.cache_misses}")
```

### B. **Manueller Cache-Access**

```python
from photo_cleaner.cache import ImageCacheManager

cache = ImageCacheManager(db.conn)

# Lookup
entry = cache.lookup(Path("photo.jpg"))
if entry:
    print(f"Found: {entry.quality_score}")

# Bulk Lookup
paths = [Path("a.jpg"), Path("b.jpg"), Path("c.jpg")]
uncached, cached = cache.bulk_lookup(paths)
print(f"{len(cached)} aus Cache, {len(uncached)} neu analysieren")

# Clear Cache
cache.clear_cache(older_than_days=30)  # Entries > 30 Tage löschen
cache.clear_cache(older_than_days=None)  # Alles löschen
```

### C. **Force Re-Analyze**

```python
# Option 1: Pipeline-Level
config = PipelineConfig(force_reanalyze=True)
pipeline = PhotoCleanerPipeline(db, config)

# Option 2: Per-File
entry = cache.lookup(file_path, force_reanalyze=True)  # Ignoriert Cache
```

---

## CLI (Command-Line Interface)

### Installation

Cache-CLI ist als Modul ausführbar:

```bash
python -m photo_cleaner.cache.cli --db /path/to/db.sqlite [COMMAND]
```

### Befehle

#### 1. **Show Statistics**

```bash
python -m photo_cleaner.cache.cli --db db.sqlite show-stats
```

Output:
```
============================================================
IMAGE CACHE STATISTICS
============================================================
Total entries:        1024
Average quality:      82.50
Top-N entries:        256
Oldest entry:         2026-01-20T10:30:00
Newest entry:         2026-01-25T15:45:00

SESSION STATISTICS
------------------------------------------------------------
Cache hits:           512
Cache misses:         512
Cache updates:        128
Hit rate:             50.0%
============================================================
```

#### 2. **Clear All Cache**

```bash
python -m photo_cleaner.cache.cli --db db.sqlite clear-all --yes
```

#### 3. **Clear Old Entries**

```bash
python -m photo_cleaner.cache.cli --db db.sqlite clear-old --days 30
```

#### 4. **Query by Quality Range**

```bash
python -m photo_cleaner.cache.cli --db db.sqlite query-quality --min 80 --max 95
```

#### 5. **Query Top-N Entries**

```bash
python -m photo_cleaner.cache.cli --db db.sqlite query-top-n --limit 5
```

---

## GUI (Graphical User Interface)

### Cache Management Dialog

Im Modern Window kann man via Menü auf den Cache zugreifen:

```python
from photo_cleaner.cache.cache_dialog import CacheManagementDialog

dialog = CacheManagementDialog(cache_manager, parent=window)
if dialog.exec() == QDialog.Accepted:
    settings = dialog.get_cache_settings()
    print(f"Use cache: {settings['use_cache']}")
    print(f"Force reanalyze: {settings['force_reanalyze']}")
```

### Dialog-Features

- **Cache Statistics**: Live-Anzeige von Einträgen, Hit-Rate, Alterung
- **Clear Controls**: Cache löschen (alle oder nach Alter)
- **Settings**: Enable/Disable, Force-Reanalyze-Flag

---

## Performance-Analyse

### Szenario 1: Erste Analyse (N=1000 Bilder)

```
Indexing:           2s  (lokale Hashing)
Duplicates:         5s  (Clustering)
Cheap Filter:       8s  (OpenCV)
Quality Analysis:   300s (MediaPipe für 200 Duplikate)
Scoring:            5s
────────────────────
TOTAL:              320s (~5 Minuten)
```

### Szenario 2: Zweiter Scan (gleiche Bilder, 100% Cache Hit)

```
Indexing:           2s  (lokale Hashing)
Duplicates:         5s  (Clustering)
Cheap Filter:       8s  (OpenCV)
Quality Analysis:   20s (Cache Lookups + DB Queries, 0 MediaPipe)
Scoring:            5s
────────────────────
TOTAL:              40s (~40 Sekunden)
Speedup:            8x schneller!
Time Saved:         280s (~4 Minuten)
```

### Szenario 3: Zweiter Scan (200 neue Bilder + 800 gecacht)

```
Indexing:           2s
Duplicates:         5s
Cheap Filter:       8s
Quality Analysis:   150s (Cache: 800 Hit + MediaPipe: 200 Miss)
Scoring:            5s
────────────────────
TOTAL:              170s (~3 Minuten)
Speedup:            ~2x schneller
```

---

## Technische Details

### Hash-Algorithmus

- **Standard**: SHA1 (40-Zeichen Hex)
- **Alternativen**: MD5 (schneller, aber weniger sicher), pHash (für Content)

```python
hash = ImageCacheManager.compute_file_hash(
    Path("img.jpg"),
    algorithm="sha1"  # oder "md5"
)
```

### Metadata Speicherung

Optional können Metadaten mit jedem Cache-Eintrag gespeichert werden:

```python
cache.store(
    file_path,
    quality_score=85.0,
    top_n_flag=True,
    metadata={
        "faces_detected": 2,
        "laplacian_variance": 123.45,
        "brightness": 150,
        "width": 1920,
        "height": 1080,
    }
)

# Später abrufen
entry = cache.lookup(file_path)
print(entry.metadata["faces_detected"])
```

### Pipeline-Versionierung

Cache wird versioniert, um Inkompatibilität zu vermeiden:

```python
ImageCacheManager.PIPELINE_VERSION = 1

# Bei Breaking Changes:
ImageCacheManager.PIPELINE_VERSION = 2
# → Alte Cache-Einträge werden automatisch ignoriert
```

---

## Fehlerbehandlung & Edge-Cases

### 1. **Datei gelöscht/verschoben**

```python
entry = cache.lookup(Path("old_location/img.jpg"))
# → None (neue Datei an neuem Ort hat anderes SHA1)
```

### 2. **Datei überschrieben (Inhalt geändert)**

```python
# Alt: SHA1 = "abc123"
# Neu: SHA1 = "def456"
entry = cache.lookup(Path("img.jpg"))  # None
# Neue Analyse wird durchgeführt → Korrekt!
```

### 3. **Beschädigte Datenbank**

```python
try:
    entry = cache.lookup(file_path)
except sqlite3.Error as e:
    logger.error(f"Cache error: {e}")
    # Fallback: Führe Analyse ohne Cache aus
```

### 4. **Cache korrupt**

```python
# Manuell löschen
cache.clear_cache(older_than_days=None)

# Oder über CLI
python -m photo_cleaner.cache.cli --db db.sqlite clear-all --yes
```

---

## Best Practices

### 1. **Cache aktivieren (Standard)**

```python
# Empfohlen
config = PipelineConfig(use_cache=True)  # Default

# Oder explizit
pipeline = PhotoCleanerPipeline(db, PipelineConfig(use_cache=True))
```

### 2. **Regelmäßig alte Einträge löschen**

```python
# Monatlich Cache aufräumen
cache.clear_cache(older_than_days=30)
```

### 3. **Force-Reanalyze nur bei Bedarf**

```python
# NUR wenn MediaPipe/Modell aktualisiert wurde
config = PipelineConfig(force_reanalyze=True)
pipeline = PhotoCleanerPipeline(db, config)
```

### 4. **Cache-Statistiken monitoren**

```python
stats = cache.get_cache_stats()
if stats.cache_hits / (stats.cache_hits + stats.cache_misses) < 0.5:
    logger.warning("Low cache hit rate - consider clearing old entries")
```

---

## Unit-Tests

Alle Cache-Funktionen sind umfassend getestet:

```bash
pytest tests/test_image_cache_manager.py -v
```

Test-Coverage:
- ✓ Cache-Speicherung und -Abruf
- ✓ Hash-Berechnung
- ✓ Bulk-Operationen
- ✓ Cache-Clearing
- ✓ Fehlerbehandlung
- ✓ Metadaten-Speicherung
- ✓ Versionierung
- ✓ Query-Builder

---

## Migration & Debugging

### Bestehendes System ohne Cache

Wenn Sie ein bestehendes PhotoCleaner-Projekt haben:

```python
# ALT: Ohne Cache
stats = run_final_pipeline(folder, db_path)

# NEU: Mit automatischem Cache
stats = run_final_pipeline(
    folder,
    db_path,
    use_cache=True  # Neuer Parameter
)
```

### Cache-Größe prüfen

```python
size_info = cache.get_cache_size()
print(f"DB entries: {size_info['entries']}")
print(f"Avg quality: {size_info['avg_quality_score']}")
```

### Logs durchsuchen

```bash
# Grep für Cache-Events
grep -i "cache" logfile.log | head -20
# Cache hit for sunset.jpg: score=85.50, top_n=True
# Cache miss for family.jpg
# Cleared cache entries older than 30 days
```

---

## Zusammenfassung

| Aspekt | Details |
|--------|---------|
| **Speedup** | 2-8x schneller bei wiederholten Scans |
| **Overhead** | ~100ms Hash-Berechnung pro Datei |
| **Speicher** | ~1KB pro Cache-Eintrag (~1MB für 1000 Bilder) |
| **API** | Transparent zur bestehenden Pipeline |
| **Testing** | 15+ Unit-Tests, vollständige Coverage |
| **Safety** | Versioning, Fallback, Error-Handling |

**Empfehlung**: Cache **immer aktivieren** für produktive Nutzung.
