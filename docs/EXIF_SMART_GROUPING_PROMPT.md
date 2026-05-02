# EXIF Smart Grouping: Implementierungs-Prompt

**Kopierbar für nächste Phase:**

---

## Title
EXIF Smart Grouping: Gruppierung nach Ort + Datum mit Reverse Geocoding, Caching & Fallback-Logik

## Role & Stance
Du bist ein Expert für EXIF-Metadaten, Geodatenverarbeitung, API-Integration und caching-Strategien. Schreibe praxisnahen, wartbaren Code mit klarem Error-Handling und Offline-Fallbacks für Windows-Umgebungen.

## Task
Erzeuge eine umfassende Lösung für EXIF Smart Grouping, die:

- **Bilder nach Ort + Datum gruppiert:** Extrahiere GPS-Koordinaten (Latitude/Longitude) aus EXIF-Daten, konvertiere zu Ort-Namen via Reverse Geocoding (OSM Nominatim)
- **Offline-Caching implementiert:** Speichere Geocoding-Ergebnisse lokal, um API-Calls zu minimieren und Offline-Betrieb zu ermöglichen
- **Fallback-Logik bei fehlenden Daten:** Nutze alternative EXIF-Quellen (Kamera-Modell, Zeitstempel-Cluster), stelle Geo-less-Gruppen bereit
- **UI-Visualisierung:** Optionale Map-Darstellung (Leaflet/Folium für Quick-Prototype, integriert in Qt-WebView)
- **Datenbank-Integration:** Speichere gruppierte Metadaten persistent in SQLite (Erweiterung bestehender Schema)

## Context

**Bestehende Infrastruktur:**
- PhotoCleaner v0.8.7 mit PySide6-UI, SQLite DB, EXIF-Extraktion (siehe `src/photo_cleaner/analysis/rating_worker.py`)
- FREE-Lizenz: 250 Bilder pro Scan · PRO: unbegrenzt
- Existing DuplicateFinder + RatingWorkerThread läuft nach Indexierung
- Windows 10/11 primary target

**Anforderungen aus Roadmap (Mai-Juni 2026):**
- Gruppierung nach Ort + Datum (geografische + zeitliche Dimensionen)
- Reverse Geocoding via OSM Nominatim (kostenlos, selbst-gehostet möglich)
- Caching + Fallback bei fehlenden GPS/EXIF-Daten
- Priorität: HOCH · Timeline: 2 Wochen

**API-Details (falls relevant):**
- **OSM Nominatim:** `https://nominatim.openstreetmap.org/reverse?format=json&lat=<LAT>&lon=<LON>`
- Rate-Limit: 1 req/sec (User-Agent erforderlich), kostenlos
- Response-Zeit: 100-500ms durchschnittlich
- Fallback: Offline-Koordinaten-Cache + Local GeoNames-DB (optional)

**Inputs:**
- EXIF-Daten: GPS-Koordinaten aus Photo EXIF (bereits teilweise extrahiert via RatingWorkerThread)
- Datum/Zeit: EXIF DateTimeOriginal für Zeitstempel-Clustering
- User-Kontext: FolderSelectionDialog, GalleryView, ReviewPanel

## Outputs Required

1. **Konzeptdokumentation** (deutsch)
   - Architektur: Komponenten, Datenfluss, Caching-Strategie
   - Designentscheidungen: Warum Nominatim? Caching-TTL? Fallback-Hierarchie?
   - Datenbank-Schema (neue Tabellen/Spalten)

2. **Code-Beispiele & Skelette**
   - `ExifGroupingEngine`: EXIF-Metadaten extrahieren + gruppieren
   - `GeocodingCache`: Lokales Caching für Reverse-Geocoding
   - `GeolocationFallback`: Strategien bei fehlenden GPS-Daten
   - `GeovisualizationWidget`: Qt-Widget mit Leaflet-Map (optional)

3. **Integration-Leitfaden**
   - Wo einfügen in bestehende Architektur (z.B. nach RatingWorkerThread)
   - DB-Migrations-Script
   - AppConfig-Parameter
   - Signal/Slot-Integration mit UI

4. **Testplan**
   - Unit-Tests: Geocoding, Caching, Fallbacks
   - E2E-Tests: EXIF-Extraktion → Gruppierung → UI-Anzeige
   - Edge-Cases: Keine GPS-Daten, ungültige Koordinaten, API-Fehler

5. **Deployment & Rollout**
   - Offline-Caching-Strategie (Größe, TTL, Cleanup)
   - API-Rate-Limiting & Error-Handling
   - Troubleshooting für Windows (Proxy, DNS, Firewall)

## Constraints & Do-nots

- ✅ Nutze OSM Nominatim (kostenlos, Open-Source, keine API-Keys)
- ✅ Offline-First: Cache alles lokal, API-Calls nur bei neuen Koordinaten
- ✅ Fallback-Hierarchie: GPS → Kamera-Ort-Metadaten → Zeitstempel-Clustering → Ungrouped
- ✅ Behalte bestehende Rating/Duplicate-Logik unverändert
- ✅ Keine Breaking Changes in DB-Schema
- ❌ Keine Google Maps (kostenpflichtig, Privacy-Issues)
- ❌ Keine 3rd-Party Map-Library im Hauptpfad (optional nur für Preview)
- ❌ Keine Netzwerk-Requests während Cancel/Shutdown
- ❌ Keine Privacy-Sendung von GPS-Daten an fremde Server (local-only)

## Examples / References

- **EXIF GPS Format:** `(40.7128, -74.0060)` = New York (Decimal Degrees)
- **Nominatim Response:** `{"address": {"city": "New York", "country": "United States"}, ...}`
- **Caching-Beispiel:** `{(40.7128, -74.0060): {"city": "New York", "cached_at": "2026-05-02"}}`
- **Fallback-Datum-Cluster:** Gruppiere Bilder mit gleichem Tag, wenn GPS fehlt

## Execution Checklist (für Implementierer)

- [ ] Verstehe Anforderungen: Gruppierung, Geocoding, Caching, Fallback
- [ ] Definiere Datenbank-Schema (neue Tabellen/Spalten)
- [ ] Implementiere ExifGroupingEngine (Extraktion + Gruppierung)
- [ ] Implementiere GeocodingCache (SQLite + Memory-Cache)
- [ ] Implementiere GeolocationFallback (3-Tier-Strategie)
- [ ] Erstelle Unit-Tests + Integration-Tests
- [ ] Integriere in modern_window.py (Signal/Slot)
- [ ] Erstelle UI-Preview (optionale Leaflet-Map)
- [ ] Dokumentiere API + Troubleshooting
- [ ] Smoke-Test auf Win10/Win11 (Offline + Online Modi)

## Conflict Resolution

Falls Anforderungen kollidieren:
1. Priorität: Offline-First & Performance vor UI-Schönheit
2. Priorität: Fallback-Robustheit vor Feature-Vollständigkeit
3. Bei ungeklärten Details: Nutze Platzhalter `[FILL: ...]` und erkläre

---

**Diese Anfrage ist produktionsreif und kann direkt an LLM gegeben werden.**
