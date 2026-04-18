# Feature Plan: Gallery View + Watch Folders
**Stand:** 18. April 2026  
**Version:** v0.9.0 (Ziel nach Implementierung)  
**Status:** Planungsphase — bereit zur Implementierung

---

## Überblick: Die Vision

PhotoCleaner soll sich vom "einmaligen Scan-Tool" zum **dauerhaften Foto-Management-System** entwickeln.

**Heute:**
```
Ordner auswählen → Analysieren → Gruppen reviewen → Löschen/Exportieren → Fertig
```

**Nach dieser Phase:**
```
Watch Folder läuft im Hintergrund
→ Neue Fotos kommen rein → automatisch verarbeitet
→ Gallery View zeigt alle KEEP-Fotos immer aktuell
→ Nutzer entscheidet nur noch die wirklich wichtigen Sachen
```

---

## Feature 1: Gallery View

### 1.1 Was ist das?

Ein neuer UI-Modus, der nach dem Review-Prozess erreichbar ist — und jederzeit.  
Zeigt alle Bilder mit Status `KEEP` in einer modernen, masonry-ähnlichen Galerie.  
**Kein Review-Modus**, kein Gruppen-Fokus — reine Anzeige der "Gewinner".

### 1.2 User Flow

```
[Review abgeschlossen] → "Galerie anzeigen"-Button erscheint
        ↓
GalleryView öffnet sich (neues QStackedWidget-Page ODER separates Fenster)
        ↓
Bilder in Masonry-Grid, sortierbar nach: Datum | Ordner | Qualitätsscore
        ↓
Klick auf Bild → Vollbild (ZoomableImageView — bereits vorhanden)
        ↓
Rechtsklick → Kontextmenü: Status ändern | Ordner öffnen | Exportieren
        ↓
[Optional] Slideshow-Modus (Auto-Advance alle N Sekunden)
```

### 1.3 Architektur

```
src/photo_cleaner/ui/
├── gallery/
│   ├── __init__.py
│   ├── gallery_view.py          ← Haupt-Widget (GalleryView)
│   ├── gallery_card.py          ← GalleryCard (leichtgewichtiger als ThumbnailCard)
│   ├── gallery_filter_bar.py    ← FilterBar (Datum, Ordner, Score-Range)
│   └── gallery_slideshow.py     ← SlideshowController
```

**GalleryView ist ein QWidget**, das in `ModernMainWindow` als neuer Stack-Page eingebunden wird.

### 1.4 Neue Daten-Query

```sql
SELECT
    f.file_id,
    f.path,
    f.quality_score,
    f.sharpness_component,
    f.lighting_component,
    f.resolution_component,
    f.face_quality_component,
    f.is_recommended,
    f.keeper_source
FROM files f
WHERE f.status = 'KEEP'
  AND f.is_deleted = 0
ORDER BY f.quality_score DESC NULLS LAST, f.path ASC
```

### 1.5 Kern-Klassen

#### `GalleryView(QWidget)`
```python
class GalleryView(QWidget):
    # Signals
    image_status_changed = Signal(Path, str)   # Rückkanal → ModernMainWindow
    gallery_closed = Signal()
    
    def __init__(self, db_path: Path, parent=None): ...
    def load_keep_images(self) -> None: ...          # Query + Lazy-Load
    def refresh(self) -> None: ...                    # Nach externem Status-Change
    def set_filter(self, filter_opts: GalleryFilterOptions) -> None: ...
```

#### `GalleryCard(QWidget)`
- Smaller footprint als `ThumbnailCard` — nur für Galerie
- Kein Checkbox (keine Mehrfachauswahl nötig im initialen Scope)
- Hover: blende EXIF-Snippet ein (Datum + Kamera)
- Rechtsklick-Kontextmenü: Status ändern, Ordner öffnen

#### `GalleryFilterBar(QWidget)`
```
[Alle] [Heute] [Diese Woche] [Dieser Monat]   |   Ordner ▾   |   Score ≥ [__]%   |   🔍 Suche
```

### 1.6 Integration in ModernMainWindow

`ModernMainWindow` hat bereits einen `QStackedWidget`-Pattern (implizit via Panels).  
Wir fügen Galerie als **neuen Tab/Button in der Sidebar** ein:

```
Sidebar (links):
  [📂 Scan starten]
  [🔍 Review]         ← heute
  [🖼 Galerie]         ← NEU
  [⚙ Einstellungen]
```

Der "Galerie öffnen"-Button in der Hauptansicht nach Abschluss des Reviews leitet weiter.

### 1.7 Performance-Strategie

- **Lazy Loading**: Thumbnails nur für sichtbare Karten laden (wie im aktuellen Grid)
- **Paginierung**: 100 Bilder pro Seite (vs. 60 heute — Galerie ist weniger dicht)
- **Thumbnail-Größe**: 200×200px (vs. 160×160px heute — Galerie braucht mehr Platz)
- **Masonry statt festes Grid**: `QFlowLayout` oder manuelles Positioning mit variablen Höhen  
  *Initial: festes Grid ist einfacher, Masonry als v1.1-Upgrade*

### 1.8 Slideshow-Modus (Optional, aber einfach)

```python
class SlideshowController:
    def __init__(self, gallery_view: GalleryView): ...
    def start(self, interval_ms: int = 3000): ...   # QTimer
    def stop(self): ...
    def next(self): ...
    def previous(self): ...
```

---

## Feature 2: Watch Folders / Auto-Import

### 2.1 Was ist das?

PhotoCleaner überwacht einen oder mehrere Ordner dauerhaft.  
Wenn neue Bilder erkannt werden, werden sie automatisch in die Pipeline eingespeist  
(Indexing → Duplicate-Finding → Analyse) — ohne manuelles "Scan starten".

### 2.2 User Flow

```
Einstellungen → "Watch Folders" → [+ Ordner hinzufügen]
        ↓
WatchFolderService läuft im Hintergrund (QThread)
        ↓
Neue .jpg/.png/.heic-Datei erkannt in überwachtem Ordner
        ↓
Debounce: warte 2 Sekunden (bis Datei vollständig geschrieben)
        ↓
Datei zur Indexing-Queue hinzufügen
        ↓
Notification in der Statusbar: "3 neue Bilder erkannt — Analyse läuft..."
        ↓
Analyse läuft im Hintergrund
        ↓
Toast/Badge: "3 neue Bilder analysiert — Galerie aktualisieren?"
```

### 2.3 Abhängigkeit: watchdog

```
pip install watchdog
```

`watchdog` ist die Standardbibliothek für Filesystem-Events in Python.  
Unterstützt Windows (ReadDirectoryChangesW), macOS (FSEvents), Linux (inotify).

Hinzufügen zu `requirements.txt` und `pyproject.toml`.

### 2.4 Architektur

```
src/photo_cleaner/
├── services/
│   ├── watch_folder_service.py   ← NEU: WatchFolderService
│   └── ...
├── ui/
│   ├── watch_folder_settings.py  ← NEU: UI-Komponente für Einstellungen
│   └── ...
```

### 2.5 DB-Schema: Neue Tabelle `watch_folders`

```sql
CREATE TABLE IF NOT EXISTS watch_folders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT NOT NULL UNIQUE,
    enabled     INTEGER NOT NULL DEFAULT 1,
    recursive   INTEGER NOT NULL DEFAULT 1,
    added_at    TEXT NOT NULL DEFAULT (datetime('now')),
    last_scan   TEXT
);
```

Migration: `src/photo_cleaner/db/migrations/004_watch_folders.sql`

### 2.6 Kern-Klasse: `WatchFolderService`

```python
class WatchFolderService(QThread):
    """Überwacht Ordner und triggert Indexing bei neuen Dateien."""
    
    # Signals
    new_files_detected = Signal(list)      # [Path, ...] — neue Dateien
    watch_error = Signal(str, str)         # (folder_path, error_msg)
    status_changed = Signal(str)           # Status-Text für UI

    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.tiff', '.webp'}
    DEBOUNCE_MS = 2000  # warte auf abgeschlossene Schreibvorgänge

    def __init__(self, db_path: Path): ...
    
    def add_watch(self, folder: Path, recursive: bool = True) -> None: ...
    def remove_watch(self, folder: Path) -> None: ...
    def get_watches(self) -> list[WatchEntry]: ...
    
    def run(self) -> None: ...        # watchdog Observer läuft hier
    def stop(self) -> None: ...
```

#### Debounce-Mechanismus (wichtig für Windows)

Windows sendet mehrere Events pro Datei-Kopiervorgang.  
Debounce verhindert, dass eine Datei dreimal analysiert wird:

```python
class _DebounceHandler(FileSystemEventHandler):
    def __init__(self, callback, debounce_ms: int = 2000):
        self._pending: dict[str, QTimer] = {}   # path → timer
        self._callback = callback
        self._debounce_ms = debounce_ms
    
    def on_created(self, event):
        if not event.is_directory:
            self._schedule(event.src_path)
    
    def on_moved(self, event):
        if not event.is_directory:
            self._schedule(event.dest_path)
    
    def _schedule(self, path: str):
        if path in self._pending:
            self._pending[path].stop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._fire(path))
        timer.start(self._debounce_ms)
        self._pending[path] = timer
    
    def _fire(self, path: str):
        self._pending.pop(path, None)
        ext = Path(path).suffix.lower()
        if ext in WatchFolderService.SUPPORTED_EXTENSIONS:
            self._callback(Path(path))
```

#### Windows-spezifisches Lock-Handling

Beim Kopieren von einer SD-Karte kann die Datei noch gesperrt sein:

```python
def _is_file_ready(path: Path) -> bool:
    """Prüft ob eine Datei vollständig geschrieben und lesbar ist."""
    try:
        with open(path, 'rb') as f:
            f.read(1)
        return True
    except (OSError, PermissionError):
        return False
```

### 2.7 Integration in ModernMainWindow

```python
# In ModernMainWindow.__init__:
self._watch_service = WatchFolderService(self._db_path)
self._watch_service.new_files_detected.connect(self._on_new_files_from_watch)
self._watch_service.start()

# Handler:
def _on_new_files_from_watch(self, paths: list[Path]) -> None:
    # 1. Benachrichtigung anzeigen (Toast/StatusBar)
    self._status_bar.showMessage(f"{len(paths)} neue Bilder erkannt — Analyse läuft...")
    # 2. Indexing-Queue befüllen
    self._trigger_incremental_index(paths)
    # 3. Nach Analyse: Galerie-Badge aktualisieren
```

### 2.8 Settings-UI: `WatchFolderSettingsWidget`

```
┌─────────────────────────────────────────────────────┐
│  Watch Folders (Auto-Import)                       ●ON│
├─────────────────────────────────────────────────────┤
│  Überwachte Ordner:                                  │
│  ┌─────────────────────────────────┬──────┬───────┐  │
│  │ C:\Users\...\Bilder             │ rek. │  [✕]  │  │
│  │ D:\Kamera Import                │ rek. │  [✕]  │  │
│  └─────────────────────────────────┴──────┴───────┘  │
│                          [+ Ordner hinzufügen]        │
│                                                       │
│  Debounce: [2] Sekunden                              │
│  ☑ Benachrichtigung bei neuen Bildern                │
└─────────────────────────────────────────────────────┘
```

---

## Zusammenspiel: Gallery View + Watch Folders

```
WatchFolderService
      │ new_files_detected
      ▼
ModernMainWindow._on_new_files_from_watch
      │
      ├─→ IncrementalIndexingThread (neue Dateien indexieren)
      │         │ finished
      │         ▼
      │   RatingWorkerThread (neue Dateien analysieren)
      │         │ finished
      │         ▼
      └─→ GalleryView.refresh()  ← Galerie zeigt neue KEEP-Bilder automatisch
```

---

## Implementierungs-Reihenfolge

### Sprint 1 (Gallery View — ~3-4 Tage)
1. `GalleryFilterOptions` Dataclass
2. `GalleryCard` Widget (vereinfachte ThumbnailCard)
3. `GalleryView` Widget (Grid + FilterBar + Pagination)
4. Integration in `ModernMainWindow` (neuer Tab in Sidebar + Button nach Review)
5. Tests: `tests/ui/test_gallery_view.py`

### Sprint 2 (Watch Folders — ~3-4 Tage)
1. DB-Migration: `watch_folders` Tabelle
2. `WatchFolderService` (watchdog + Debounce + Lock-Check)
3. `WatchFolderRepository` (CRUD für watch_folders)
4. `WatchFolderSettingsWidget` (UI in Settings-Dialog)
5. Integration in `ModernMainWindow`
6. Tests: `tests/services/test_watch_folder_service.py`

### Sprint 3 (Zusammenspiel — ~1-2 Tage)
1. Inkrementelles Indexing-Trigger-Pfad
2. GalleryView auto-refresh nach Watch-Import
3. End-to-End-Test: Datei kopieren → erscheint in Galerie

---

## Wichtige Design-Entscheidungen

| Frage | Entscheidung | Begründung |
|---|---|---|
| Gallery als neues Fenster oder neuer Tab? | **Neuer Tab** in ModernMainWindow | Konsistent mit bestehendem UX-Muster |
| Masonry oder festes Grid? | **Festes Grid** (initial) | Einfacher, konsistent mit bestehenden Cards |
| Watch Folders in Echtzeit oder Poll? | **Echtzeit** via watchdog | Windows-native Events, kein CPU-Overhead |
| Wo Watch-Config speichern? | **DB** (watch_folders Tabelle) | Konsistent mit restlicher App-Config |
| Slideshow initial oder v1.1? | **Initial** (einfach via QTimer) | 10 Zeilen Code, großer UX-Gewinn |
| PRO-Feature oder FREE? | **FREE** (Gallery), **PRO** (Watch Folders) | Watch Folders = Power-User-Feature |

---

## Dateien die erstellt/verändert werden

### Neu erstellt:
- `src/photo_cleaner/ui/gallery/__init__.py`
- `src/photo_cleaner/ui/gallery/gallery_view.py`
- `src/photo_cleaner/ui/gallery/gallery_card.py`
- `src/photo_cleaner/ui/gallery/gallery_filter_bar.py`
- `src/photo_cleaner/ui/gallery/gallery_slideshow.py`
- `src/photo_cleaner/services/watch_folder_service.py`
- `src/photo_cleaner/repositories/watch_folder_repository.py`
- `src/photo_cleaner/ui/watch_folder_settings.py`
- `src/photo_cleaner/db/migrations/004_watch_folders.sql`
- `tests/ui/test_gallery_view.py`
- `tests/services/test_watch_folder_service.py`

### Verändert:
- `src/photo_cleaner/ui/modern_window.py` (Gallery-Tab + Watch-Service-Init)
- `src/photo_cleaner/ui/settings_dialog.py` (Watch Folders Tab)
- `src/photo_cleaner/db/schema.py` (Migration ausführen)
- `src/photo_cleaner/db/migrations.py` (004 registrieren)
- `requirements.txt` (watchdog hinzufügen)
- `pyproject.toml` (watchdog dependency)

---

## i18n: Neue Schlüssel (DE/EN + alle 4 Locales)

```python
# In i18n.py hinzufügen:
"gallery_title": "Galerie",
"gallery_keep_empty": "Keine Bilder mit Status KEEP vorhanden.",
"gallery_filter_all": "Alle",
"gallery_filter_today": "Heute",
"gallery_filter_week": "Diese Woche",
"gallery_filter_month": "Dieser Monat",
"gallery_filter_score": "Score ≥",
"gallery_slideshow_start": "Diashow starten",
"gallery_slideshow_stop": "Diashow stoppen",
"gallery_open_button": "Galerie öffnen",
"watch_folders_title": "Watch Folders",
"watch_folders_enabled": "Ordner-Überwachung aktiv",
"watch_folders_add": "+ Ordner hinzufügen",
"watch_folders_remove": "Entfernen",
"watch_folders_recursive": "Unterordner einschließen",
"watch_folders_new_detected": "{count} neue Bilder erkannt",
"watch_folders_analyzing": "Werden analysiert...",
"watch_folders_pro_only": "Watch Folders ist ein PRO-Feature",
```

---

## Risiken und Mitigationen

| Risiko | Mitigation |
|---|---|
| watchdog erhöht Frozen-Build-Größe | watchdog ist klein (~200KB), kein Problem |
| Windows-Locking bei SD-Karten-Import | `_is_file_ready()` Check + 3× Retry mit 500ms Delay |
| Gallery bei 10.000+ Bildern träge | Paginierung (100/Seite) + Lazy Thumbnails |
| Galerie zeigt veraltete Daten nach Status-Änderung | `GalleryView.refresh()` Signal-Kette |
| watchdog thread-safety mit Qt | Events über `Signal.emit()` (thread-safe in Qt) |

---

*Nächster Schritt: Sprint 1 starten — GalleryView implementieren.*
