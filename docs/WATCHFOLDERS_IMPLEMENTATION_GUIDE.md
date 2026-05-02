# Watchfolders & Autoimport: Implementierungs-Leitfaden

**Zielgruppe:** Entwickler (nächste Phase)  
**Komplexität:** Mittel  
**Geschätzter Aufwand:** 3-5 Tage für Full Integration + Testing  

---

## Quick Start

### 1. Komponenten sind bereit!

Die folgenden Dateien sind bereits implementiert:

```
src/photo_cleaner/autoimport/
├── __init__.py                  ✅ Paket-Einstiegspunkt
├── watchfolder_monitor.py       ✅ QFileSystemWatcher-Wrapper (100% complete)
├── debounced_event_handler.py   ✅ Debounce-Logik (100% complete)
├── autoimport_pipeline.py       ⏳ Placeholder für DuplicateFinder/RatingWorker Integration
└── autoimport_controller.py     ✅ Hauptkoordinator (100% complete)

tests/
└── test_autoimport_components.py ✅ Unit-Tests (bereit für pytest)
```

### 2. Nächste Schritte (in dieser Reihenfolge)

```
Phase 1: INTEGRATION (1-2 Tage)
  ├─ [ ] Integriere AutoimportController in modern_window.py
  ├─ [ ] Verbinde Signale mit UI-Callbacks
  └─ [ ] Erweitere AppConfig um autoimport_enabled

Phase 2: PIPELINE-FILL (1-2 Tage)
  ├─ [ ] Implementiere autoimport_pipeline._find_duplicates() mit DuplicateFinder
  ├─ [ ] Implementiere autoimport_pipeline._rate_images() mit RatingWorkerThread
  └─ [ ] Implementiere autoimport_pipeline._save_rating_to_db()

Phase 3: TESTING & POLISH (1 Tag)
  ├─ [ ] Führe Unit-Tests aus (pytest tests/test_autoimport_components.py)
  ├─ [ ] E2E-Tests (Szenarien 1-7 aus WATCHFOLDERS_AUTOIMPORT.md)
  └─ [ ] Performance-Optimierung, Logging-Audit
```

---

## Phase 1: Integration in modern_window.py

### 1.1 Import hinzufügen (zeile ~10)

```python
from photo_cleaner.autoimport.autoimport_controller import AutoimportController
```

### 1.2 In `__init__()` initialisieren (ca. zeile 450, nach Worker-Initialisierung)

Suche:
```python
# Indexing thread
self._indexing_thread = IndexingThread(...)
```

Füge nach allen Worker-Initialisierungen hinzu:

```python
# ===== NEU: Autoimport-Integration =====
self._autoimport_controller = AutoimportController(
    db_path=self.db_manager.db_path,
    config=self.app_config,
    license_manager=self.license_manager,
    parent=self
)

# Signale verbinden
self._autoimport_controller.status_changed.connect(self._on_autoimport_status)
self._autoimport_controller.import_complete.connect(self._on_autoimport_complete)
# ===== /NEU =====
```

### 1.3 Callback-Methoden hinzufügen (am Ende der Klasse, vor closeEvent)

```python
def _on_autoimport_status(self, status: str):
    """Callback: Autoimport-Status ändert sich."""
    logger.info(f"Autoimport-Status: {status}")
    # Optional: Status in UI-Label anzeigen (z.B. Statusbar)
    # self.statusBar().showMessage(status, 5000)


def _on_autoimport_complete(self, result: dict):
    """Callback: Autoimport-Analyse abgeschlossen."""
    logger.info(f"Autoimport-Ergebnis: {result['total_files']} Dateien, "
               f"{result['duplicates_found']} Duplikate")
    
    # Optional: Refresh Gallery, um neue Duplikate zu zeigen
    if self._gallery_view:
        self._refresh_gallery_data()
    
    # Optional: Notification an Benutzer
    # self._show_notification(
    #     f"✓ {result['total_files']} neue Bilder analysiert. "
    #     f"{result['duplicates_found']} Duplikate gefunden.",
    #     duration_ms=5000
    # )
```

### 1.4 In `closeEvent()` stoppen (ca. zeile ~9380)

Suche:
```python
def closeEvent(self, event: QCloseEvent):
    """Event: Fenster wird geschlossen."""
    logger.info("Closing main window")
    self._is_shutting_down = True
```

Füge nach `self._is_shutting_down = True` hinzu:

```python
    # NEU: Autoimport stoppen
    if self._autoimport_controller:
        self._autoimport_controller.shutdown()
```

### 1.5 AppConfig erweitern

**Datei:** `src/photo_cleaner/config.py` (in AppConfig.__init__)

```python
# NEU: Autoimport defaults
self.autoimport_enabled = self.get('autoimport.enabled', False)
self.autoimport_debounce_ms = self.get('autoimport.debounce_window_ms', 3000)
```

### 1.6 Startup-Hook hinzufügen

Im `ModernMainWindow` oder im Startup-Sequence (nach UI ist ready):

```python
# Nach diesem Punkt sollte Autoimport starten:
if self._autoimport_controller:
    self._autoimport_controller.startup()
```

---

## Phase 2: Pipeline-Integration

### 2.1 DuplicateFinder Integration in `autoimport_pipeline._find_duplicates()`

**Datei:** `src/photo_cleaner/autoimport/autoimport_pipeline.py`

Ersetze Placeholder-Methode:

```python
def _find_duplicates(self, file_paths: list) -> list:
    """Führt Duplikaterkennung durch."""
    
    from photo_cleaner.duplicates.finder import DuplicateFinder
    
    logger.info(f"Starten DuplicateFinder für {len(file_paths)} Dateien")
    
    finder = DuplicateFinder(
        db_path=self.db_path,
        hash_algorithm='sha256',
        phash_threshold=5  # Existing threshold (siehe duplicates/finder.py)
    )
    
    # Indexiere neue Dateien
    for idx, file_path in enumerate(file_paths):
        try:
            finder.add_file(file_path)
            self.import_progress.emit(idx, len(file_paths))
        except Exception as e:
            logger.warning(f"Fehler beim Indexieren von {file_path}: {e}")
    
    # Führe Vergleich durch
    try:
        duplicates = finder.find_duplicates()
        logger.info(f"DuplicateFinder: {len(duplicates)} Duplikate gefunden")
        return duplicates
    except Exception as e:
        logger.error(f"Fehler in DuplicateFinder: {e}", exc_info=True)
        return []
```

### 2.2 RatingWorkerThread Integration in `autoimport_pipeline._rate_images()`

**Datei:** `src/photo_cleaner/autoimport/autoimport_pipeline.py`

Ersetze Placeholder-Methode:

```python
def _rate_images(self, file_paths: list):
    """Führt Qualitätsbewertung durch."""
    
    from photo_cleaner.analysis.rating_worker import RatingWorkerThread
    
    logger.info(f"Starten RatingWorkerThread für {len(file_paths)} Dateien")
    
    # Erstelle Worker
    worker = RatingWorkerThread()
    worker.set_files(file_paths)
    
    # Verbinde Progress-Signal (optional)
    if hasattr(worker, 'progress'):
        worker.progress.connect(
            lambda curr, total: self.import_progress.emit(curr, total)
        )
    
    # Führe synchron aus (nicht start(), sondern run())
    try:
        worker.run()
        
        # Speichere Ergebnisse in DB
        if hasattr(worker, 'get_results'):
            results = worker.get_results()
            for file_path, rating_data in results.items():
                self._save_rating_to_db(file_path, rating_data)
        
        logger.info(f"RatingWorkerThread: Abgeschlossen")
    
    except Exception as e:
        logger.error(f"Fehler in RatingWorkerThread: {e}", exc_info=True)
```

### 2.3 Database-Integration in `_save_rating_to_db()`

**Datei:** `src/photo_cleaner/autoimport/autoimport_pipeline.py`

```python
def _save_rating_to_db(self, file_path: str, rating_data: dict):
    """Speichert Bewertungsergebnisse in der Datenbank."""
    
    # [FILL: Integration mit DB-Manager aus modern_window.py]
    # Beispiel-Implementierung (anpassen an tatsächliche DB-Schema):
    
    # try:
    #     from photo_cleaner.db.models import Image
    #     image = Image.query.filter_by(path=file_path).first()
    #     if image:
    #         image.blur_score = rating_data.get('blur_score')
    #         image.quality_rating = rating_data.get('quality_rating')
    #         image.exif_data = rating_data.get('exif_data')
    #         db.session.commit()
    #         logger.debug(f"Speicherte Rating für {Path(file_path).name}")
    # except Exception as e:
    #     logger.error(f"Fehler beim Speichern in DB: {e}")
    
    logger.debug(f"_save_rating_to_db: {Path(file_path).name} → {len(rating_data)} Felder")
```

---

## Phase 3: Testing

### 3.1 Unit-Tests ausführen

```bash
# Aktiviere venv
.\.venv\Scripts\Activate.ps1

# Führe Tests aus
pytest tests/test_autoimport_components.py -v

# Mit Coverage (optional)
pytest tests/test_autoimport_components.py --cov=src/photo_cleaner/autoimport -v
```

**Erwartete Ausgabe:**
```
tests/test_autoimport_components.py::TestWatchfolderMonitor::test_add_watchfolder_valid_path PASSED
tests/test_autoimport_components.py::TestWatchfolderMonitor::test_add_watchfolder_invalid_path PASSED
tests/test_autoimport_components.py::TestDebouncedEventHandler::test_handle_event_single PASSED
tests/test_autoimport_components.py::TestDebouncedEventHandler::test_handle_event_multiple_batched PASSED
...
=============== 15 passed in 0.85s ===============
```

### 3.2 E2E-Test Szenario 1: Einfacher Import

**Manuell durchführen:**

1. Starte PhotoCleaner:
   ```bash
   python run_ui.py
   ```

2. Öffne Settings/Preferences und aktiviere Autoimport (falls UI vorhanden)

3. Konfiguriere einen Testordner:
   ```
   C:\Temp\PhotoCleaner_Test\
   ```

4. Kopiere 5 Testbilder in den Ordner

5. **Prüfe Logs:**
   ```
   %APPDATA%\PhotoCleaner\watchfolders_autoimport.log
   ```
   
   Erwartete Log-Einträge:
   ```
   2026-05-02 10:30:16 [INFO] Autoimport: Analyse angefordert für 5 Dateien
   2026-05-02 10:30:16 [INFO] AutoimportPipeline: Starten Duplikaterkennung
   2026-05-02 10:30:20 [INFO] AutoimportPipeline: Abgeschlossen. 5 Dateien, 0 Duplikate
   ```

6. **Prüfe UI:** 
   - Statusbar sollte "✓ 5 neue Bilder analysiert" anzeigen (falls implementiert)
   - Gallery sollte ggf. aktualisiert werden

---

## Fehlerbehebung

### Problem: "ModuleNotFoundError: No module named 'photo_cleaner.autoimport'"

**Lösung:**
- Prüfe, dass `src/photo_cleaner/autoimport/` Ordner existiert
- Prüfe, dass `__init__.py` vorhanden ist
- Aktualisiere PYTHONPATH: `export PYTHONPATH=$PYTHONPATH:src/`

### Problem: "TypeError: QFileSystemWatcher(...) got unexpected argument"

**Lösung:**
- Prüfe PySide6-Version: `pip list | grep PySide6`
- Sollte ≥ 6.5.0 sein
- Update falls nötig: `pip install --upgrade PySide6`

### Problem: Unit-Tests schlagen fehl mit "qtbot fixture not found"

**Lösung:**
- Installiere pytest-qt: `pip install pytest-qt`
- Führe Tests mit pytest aus: `pytest tests/test_autoimport_components.py -v`

---

## Checkliste für Implementierer

- [ ] Phase 1: Integration in modern_window.py (Signale, Callbacks, Startup/Shutdown)
- [ ] Phase 2: DuplicateFinder-Integration in autoimport_pipeline.py
- [ ] Phase 3: RatingWorkerThread-Integration in autoimport_pipeline.py
- [ ] Phase 4: Unit-Tests ausführen und grün validieren
- [ ] Phase 5: E2E-Test Szenario 1 (einzelne Datei)
- [ ] Phase 6: E2E-Test Szenario 2 (Batch 100 Dateien)
- [ ] Phase 7: Logging-Audit (Verbosity, Format, Rotations)
- [ ] Phase 8: Settings-Dialog UI erweitern (Watchfolders-Management)
- [ ] Phase 9: Dokumentation updaten (README, User Guide)
- [ ] Phase 10: Code-Review & Merge zu Main

---

## Referenzen & Links

- **Hauptdokumentation:** [WATCHFOLDERS_AUTOIMPORT.md](WATCHFOLDERS_AUTOIMPORT.md)
- **Bestehende Komponenten:**
  - DuplicateFinder: `src/photo_cleaner/duplicates/finder.py`
  - RatingWorkerThread: `src/photo_cleaner/analysis/rating_worker.py`
  - AppConfig: `src/photo_cleaner/config.py`
- **Tests:** `tests/test_autoimport_components.py`
- **Roadmap:** [ROADMAP_2026.md](ROADMAP_2026.md) (Watchfolders section)

---

**Fragen? Nutze die [WATCHFOLDERS_AUTOIMPORT.md](WATCHFOLDERS_AUTOIMPORT.md) für Detail!**
