# Pipeline UI Archive

**Status:** Archived (January 2026)  
**Reason:** ITIL-UI reaktiviert als Haupt-UI

## Was ist hier archiviert?

Diese UI war Teil der Final Pipeline v2.0 Implementation:

- **pipeline_results_ui.py** - Tkinter-basierte Results UI für Pipeline
  - Zeigt Duplicate Groups mit Top-N Marking
  - Thumbnail-Vorschau mit Scores
  - Delete-Buttons mit Confirmation
  - Für `run_final_pipeline.py` entwickelt

## Warum archiviert?

Das ITIL-UI (`main_window.py`) mit PySide6 wurde als primäre UI reaktiviert:
- Umfassendere Features
- Bessere Integration mit Services
- Status-Management
- History-Tracking
- Etabliertes Design

## Wie reaktivieren?

Falls du die Pipeline-UI wieder verwenden möchtest:

```python
# 1. Datei zurück kopieren
cp pipeline_ui_archive/pipeline_results_ui.py ../pipeline_results_ui.py

# 2. In run_final_pipeline.py verwenden
from photo_cleaner.ui.pipeline_results_ui import show_pipeline_results
show_pipeline_results(db)
```

## Technische Details

- **Framework:** Tkinter (standard Python)
- **Dependencies:** PIL, tkinter (minimal)
- **Integration:** Database, FileRepository, ModeService
- **Features:** Group navigation, thumbnail preview, batch delete

---

*Archiviert am: 2026-01-04*  
*Kann jederzeit wieder aktiviert werden*
