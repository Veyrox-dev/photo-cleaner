# Projekt-Audit & Abarbeitung (2026-05-03)

## Kontext
Systematische Analyse auf Bugs, Inkonsistenzen, Risiken und Legacy/Build-Probleme.

## Priorisierte Punkte

### 1) Kritisch

- [x] Autoimport importiert falsche Qt-Signale (`pyqtSignal` statt `Signal`)  
  Dateien:  
  - `src/photo_cleaner/autoimport/autoimport_controller.py`  
  - `src/photo_cleaner/autoimport/autoimport_pipeline.py`  
  - `src/photo_cleaner/autoimport/watchfolder_monitor.py`  
  - `src/photo_cleaner/autoimport/debounced_event_handler.py`  
  Status: **gefixt**

- [x] Regression/Kompatibilitätsbruch in `QualityAnalyzer` (fehlende private Methoden)  
  Dateien:  
  - `src/photo_cleaner/pipeline/quality_analyzer.py`  
  Symptome: `_analyze_faces_haar` und `_invalidate_face_mesh_cache` fehlten auf `QualityAnalyzer`  
  Status: **gefixt** (kompatible Wrapper ergänzt)

### 2) Mittel

- [x] Ressourcenrisiko: DB-Verbindungen im Kartenwidget nicht robust geschlossen bei Exceptions  
  Datei:  
  - `src/photo_cleaner/ui/map/map_widget.py`  
  Status: **gefixt** (`with sqlite3.connect(...)`)

- [x] API-Inkonsistenz im Export/Delete-Workflow-Controller (Signaturdrift)  
  Datei:  
  - `src/photo_cleaner/ui/workflows/export_delete_workflow_controller.py`  
  Status: **gefixt** (Default-Parameter für Rückwärtskompatibilität)

- [x] Korruptes Bild: `compute_file_hash` gab trotz ungültigem Bildinhalt Hash zurück  
  Datei:  
  - `src/photo_cleaner/core/hasher.py`  
  Status: **gefixt** (Image-Validierung via PIL `verify()` vor Datei-Hash)

- [x] Build-/MSI-Risiko: Legacy/Archiv-Code wird durch Packaging breit eingesammelt  
  Dateien:  
  - `PhotoCleaner.spec` (`collect_submodules('photo_cleaner')`, breites `rglob`)  
  - `installer/PhotoCleaner.wxs` (`dist/PhotoCleaner/**`)  
  Status: **gefixt**  
  Umsetzung: Legacy-/Archiv-Module werden in `PhotoCleaner.spec` und `installer/PhotoCleaner.wxs` explizit ausgeschlossen.

- [x] Konfig-Drift: doppelte pytest-Konfiguration (`pytest.ini` + `pyproject.toml`)  
  Dateien:  
  - `pytest.ini`  
  - `pyproject.toml` (`[tool.pytest.ini_options]`)  
  Status: **gefixt** (`tool.pytest.ini_options` entfernt, `pytest.ini` ist Source of Truth)

- [x] Python-Version-Drift (`pyproject`: >=3.12, Umgebung/Test auf 3.11)  
  Datei:  
  - `pyproject.toml`  
  Status: **gefixt** (`requires-python` auf `>=3.11,<3.13`, Classifier ergänzt)

### 3) Niedrig

- [x] Broad-Exception-Hotspots entschärft (kritische Stellen)  
  Fokus zuerst:  
  - `src/photo_cleaner/ui_actions.py`  
  - `src/photo_cleaner/ui/modern_window.py`  
  - `src/photo_cleaner/pipeline/pipeline.py`
  Status: **teilweise strategisch / praktisch erledigt**  
  - Kritische Catch-Blöcke in Shutdown/Rollback/Pipeline auf spezifischere Exception-Typen umgestellt.  
  - Verbleibende breite Catch-Blöcke in `ui_actions.py` sind bewusstes Facade-Design (strukturierte Fehlerantworten statt UI-Crash).

## Legacy-Check

### Sicher entfernbar (nach Build-Adjustments)
- [x] `src/photo_cleaner/ui/pipeline_ui_archive/pipeline_results_ui.py` (**gelöscht**)
- [x] `src/photo_cleaner/ui/pipeline_ui_archive/README.md` (**gelöscht**)

### Unsicher / prüfen
- [x] `src/photo_cleaner/ui/legacy/cleanup_ui.py` (**gelöscht**, keine Laufzeitreferenzen)
- [x] `src/photo_cleaner/ui/main_window.py` (**gelöscht**, keine Laufzeitreferenzen; ModernMainWindow bleibt aktiv)

## Test-Status nach Fix-Runde
- Ziel: frühere harte Fehler/Regressionspunkte eliminieren.
- Teilstand:  
  - Kritische Importfehler im Autoimport-Modul behoben.  
  - `qtbot`-Fixture verfügbar gemacht (`pytest-qt` ergänzt/ installiert).  
  - QualityAnalyzer-Kompatibilitäts-Regressionen behoben.  
  - Korruptes-Bild-Hashing-Semantik an Tests angepasst.  
- Ausstehend: erneuter gezielter Re-Run + voller Testlauf.

## Abnahmestand (gezielte Regressionstests)
- 59/59 relevante Tests grün:  
  - `tests/test_autoimport_components.py`  
  - `tests/integration/test_cache_invalidation_race.py`  
  - `tests/integration/test_phase1_crash_prevention.py`  
  - `tests/integration/test_phase2_7_improvements.py`  
  - `tests/unit/test_export_delete_workflow_controller.py`

## Voller Testlauf
- Ergebnis: **473 passed, 3 failed**  
- Verbleibende 3 Fails sind i18n-Label-Erwartungen in `tests/unit/test_score_explanation.py` (Deutsch erwartet, Englisch geliefert) und stehen nicht in direktem Zusammenhang zu den hier umgesetzten Build-/Legacy-/Exception-Änderungen.
