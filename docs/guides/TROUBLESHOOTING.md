# PhotoCleaner Troubleshooting

**Version:** 0.8.3 (Feb 2026)

---

## Deutsch

### App startet nicht oder bricht sofort ab
- Stelle sicher, dass Python 3.12+ aktiv ist.
- Installiere Abhaengigkeiten neu:
  - `pip install -r requirements.txt`
- Starte im Debug-Modus:
  - `set PHOTOCLEANER_MODE=DEBUG` (Windows)

### OpenCV / MediaPipe Fehler
- Deaktiviere Face Mesh fuer Tests:
  - `python -m photo_cleaner.cli scan /path --no-face-mesh`
- Falls schwere Dependencies fehlen:
  - `set PHOTOCLEANER_SKIP_HEAVY_DEPS=1`

### Sehr langsame Analyse
- Verarbeite in kleineren Batches (1k-5k).
- Nutze SSD statt HDD.
- Deaktiviere Face Mesh fuer Geschwindigkeit.

### Keine Duplikate gefunden
- Stelle sicher, dass der richtige Ordner gescannt wird.
- Pruefe, ob Dateiformate unterstuetzt sind (JPG/PNG/HEIC).
- Reduziere die Distanz/Schwelle in den Einstellungen.

### Thumbnails fehlen oder sind veraltet
- Thumbnail-Cache loeschen und neu generieren.
- Cache kann gefahrlos entfernt werden.

### Lizenz kann nicht aktiviert werden
- Pruefe Internetverbindung und Systemzeit.
- Erneut versuchen und Lizenz neu speichern.
- Siehe: [LICENSE_SYSTEM.md](LICENSE_SYSTEM.md)

### Shortcuts reagieren nicht
- Klick einmal in das Hauptfenster.
- Deaktiviere ggf. globale Hotkey-Tools.

---

## English

### App does not start or exits immediately
- Ensure Python 3.12+ is active.
- Reinstall dependencies:
  - `pip install -r requirements.txt`
- Start in debug mode:
  - `set PHOTOCLEANER_MODE=DEBUG` (Windows)

### OpenCV / MediaPipe errors
- Disable Face Mesh for testing:
  - `python -m photo_cleaner.cli scan /path --no-face-mesh`
- If heavy deps are missing:
  - `set PHOTOCLEANER_SKIP_HEAVY_DEPS=1`

### Analysis is very slow
- Process in smaller batches (1k-5k).
- Use an SSD instead of HDD.
- Disable Face Mesh for speed.

### No duplicates found
- Verify the correct folder is scanned.
- Check supported formats (JPG/PNG/HEIC).
- Lower the distance/threshold in settings.

### Thumbnails missing or stale
- Clear the thumbnail cache and re-generate.
- Cache can be safely removed.

### License activation fails
- Check internet connection and system time.
- Retry and re-save the license.
- See: [LICENSE_SYSTEM.md](LICENSE_SYSTEM.md)

### Shortcuts do not respond
- Click once inside the main window.
- Disable global hotkey tools if needed.
