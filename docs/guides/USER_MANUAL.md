# PhotoCleaner User Manual / Benutzerhandbuch

**Version:** 0.8.7 (Mai 2026)

This manual is a user-focused overview. For technical details, see [docs/INDEX.md](../INDEX.md).

---

## Deutsch

### Uebersicht
PhotoCleaner hilft dir, grosse Foto-Sammlungen zu bereinigen: Duplikate finden, Qualitaet bewerten, beste Bilder markieren, sicher entscheiden.

### Schnellstart (UI)
1. Starte die App:
   - `python run_ui.py`
2. Waehle deinen Foto-Ordner.
3. Warte auf Analyse und oeffne die Ergebnis-Ansicht.
4. Treffe Entscheidungen pro Gruppe und exportiere oder loesche.

### Schnellstart (CLI)
```bash
# Scan + Duplikate + Analyse
python -m photo_cleaner.cli scan /path/to/photos

# Modern UI mit DB oeffnen
python -c "from photo_cleaner.ui.modern_window import run_modern_ui; run_modern_ui('photo_cleaner.db')"
```

### Workflow (Kurzfassung)
1. **Indexing**: Dateien erfassen
2. **Duplicates**: Aehnliche Gruppen bilden
3. **Quality**: Schaerfe, Licht, Augen, Aufloesung bewerten
4. **Auto-Auswahl**: Bestes Bild markieren (⭐)
5. **Review**: Entscheiden (KEEP/DELETE/UNSURE)
6. **Export/Cleanup**: Exportieren oder loeschen

### Modi (oben rechts)
- **SAFE**: Read-only, keine Aenderungen
- **REVIEW**: Markieren erlaubt, Loeschung nur geplant
- **CLEANUP**: Loeschungen ausfuehren

### Wichtige Shortcuts
- `K` = Keep
- `D` = Delete
- `U` = Unsure
- `Space` = Lock
- `Z` = Undo
- `Ctrl+J` / `Ctrl+K` = Naechste/Vorherige Gruppe
- `?` = Shortcuts anzeigen

Siehe auch: [FAQ.md](FAQ.md) und [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Auto-Auswahl (⭐)
Auto-Selection markiert das beste Bild pro Gruppe. Kriterien und Gewichtungen findest du in:
- [AUTO_SELECTION.md](AUTO_SELECTION.md)

### Gallery-View (neu in v0.8.5+)
Nach dem Review oeffnet sich die **Gallery**: alle KEEP-Bilder in einer Rasteransicht.
- Bilder nach Datum, Ort oder Kamera filtern
- Letzter Qualitaets-Check vor dem Export
- Bild-Status direkt in der Gallery aendern (KEEP / DELETE / UNSURE)
- Nach Watch-Folder-Import aktualisiert sich die Gallery automatisch

### EXIF Smart Grouping (neu in v0.8.6+)
PhotoCleaner gruppiert deine Keep-Bilder nach **Aufnahmeort** anhand von GPS-Daten:
- Reverse-Geocoding via OpenStreetMap (keine API-Key noetig)
- Ortsname wird im EXIF-Snippet angezeigt: "Datum | Kamera | Ort"
- **Orts-Filter** in der Gallery: Bilder einer bestimmten Stadt anzeigen
- **Karten-Ansicht**: Keep-Bilder auf einer Offline-Karte mit Standort-Markern
- Kein GPS in den Metadaten? Fallback auf Kamera-Herkunft → Datum-Cluster → Ungrouped

### Watch Folders / Auto-Import (neu in v0.8.7)
PhotoCleaner kann Ordner automatisch ueberwachen und neue Bilder selbststaendig analysieren:
1. Einstellungen → Watch Folders → Ordner hinzufuegen
2. Neue Bilder, die in diesen Ordner kopiert werden, werden automatisch indexiert
3. Duplikat-Erkennung und Qualitaetsbewertung starten im Hintergrund
4. Gallery und Review-Badge werden nach Abschluss aktualisiert
- Debounce-Fenster verhindert vorzeitige Analyse bei laufenden Kopiervoргangen
- Autoimport kann in den Einstellungen aktiviert / deaktiviert werden

### Entscheidungen & Sicherheit
- PhotoCleaner loescht nie automatisch.
- Im CLEANUP-Modus werden Loeschungen ausgefuehrt.
- Nutze **Lock** fuer wichtige Bilder.

### Export
- Export kopiert KEEP-Bilder in eine Zielstruktur (YYYY/MM/DD).
- Export ist sicher, Originale bleiben unangetastet.

### Lizenzen (Kurzinfo)
- FREE: einmalig 250 Bilder (keine Zeitbeschraenkung)
- PRO: unbegrenzte Bilder + Premium-Features (29 EUR/Jahr)
- Offline-Nutzung moeglich (mit lokalem Cache)

Details: [LICENSE_SYSTEM.md](LICENSE_SYSTEM.md)

### Performance-Tipps
- Grosse Sammlungen in Batches verarbeiten (z. B. 1k-5k).
- SSD nutzen, wenn moeglich.
- Face Mesh deaktivieren, wenn Performance kritisch ist.
- EXIF-Geocoding benoetigt eine Internetverbindung; Ergebnisse werden lokal gecacht (7 Tage TTL).

---

## English

### Overview
PhotoCleaner helps you clean large photo libraries: find duplicates, score quality, mark the best image, and decide safely.

### Quick Start (UI)
1. Launch the app:
   - `python run_ui.py`
2. Select your photo folder.
3. Wait for analysis and open results.
4. Decide per group and export or clean up.

### Quick Start (CLI)
```bash
# Scan + duplicates + analysis
python -m photo_cleaner.cli scan /path/to/photos

# Launch modern UI with DB
python -c "from photo_cleaner.ui.modern_window import run_modern_ui; run_modern_ui('photo_cleaner.db')"
```

### Workflow (Short)
1. **Indexing**: collect files
2. **Duplicates**: build similar groups
3. **Quality**: sharpness, light, eyes, resolution
4. **Auto-Selection**: mark best image (⭐)
5. **Review**: decide (KEEP/DELETE/UNSURE)
6. **Export/Cleanup**: export or delete

### Modes (top right)
- **SAFE**: read-only, no changes
- **REVIEW**: mark decisions, deletion staged
- **CLEANUP**: execute deletions

### Key Shortcuts
- `K` = Keep
- `D` = Delete
- `U` = Unsure
- `Space` = Lock
- `Z` = Undo
- `Ctrl+J` / `Ctrl+K` = Next/Previous group
- `?` = Show shortcuts

See: [FAQ.md](FAQ.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Auto-Selection (⭐)
Auto-Selection marks the best image in each group. Details:
- [AUTO_SELECTION.md](AUTO_SELECTION.md)

### Gallery View (new in v0.8.5+)
After the review, the **Gallery** opens showing all KEEP images in a grid layout.
- Filter images by date, location, or camera
- Last quality check before export
- Change image status directly in the gallery (KEEP / DELETE / UNSURE)
- After a Watch Folder import the gallery refreshes automatically

### EXIF Smart Grouping (new in v0.8.6+)
PhotoCleaner groups your keep images by **location** using GPS metadata:
- Reverse-geocoding via OpenStreetMap (no API key required)
- Location name shown in the EXIF snippet: "Date | Camera | Location"
- **Location filter** in the gallery: show images from a specific city
- **Map view**: keep images pinned on an offline map with location markers
- No GPS in metadata? Fallback: camera origin → date cluster → Ungrouped

### Watch Folders / Auto-Import (new in v0.8.7)
PhotoCleaner can watch folders and analyse new photos automatically:
1. Settings → Watch Folders → Add folder
2. New images copied to that folder are indexed automatically
3. Duplicate detection and quality scoring run in the background
4. Gallery and review badge are updated on completion
- Debounce window prevents premature analysis during active file copies
- Auto-import can be enabled / disabled in settings

### Decisions & Safety
- PhotoCleaner never deletes automatically.
- CLEANUP mode executes deletions.
- Use **Lock** for important images.

### Export
- Export copies KEEP images into a YYYY/MM/DD structure.
- Export is safe; originals remain unchanged.

### Licenses (Short)
- FREE includes one-time lifetime usage for 250 images total
- PRO unlocks unlimited analysis and premium features (€29/year)
- Offline use is supported with a signed local cache

Details: [LICENSE_SYSTEM.md](LICENSE_SYSTEM.md)

### Performance Tips
- Process large libraries in batches (e.g., 1k-5k).
- Use an SSD when possible.
- Disable Face Mesh if performance is critical.
- EXIF geocoding requires an internet connection; results are cached locally (7-day TTL).
