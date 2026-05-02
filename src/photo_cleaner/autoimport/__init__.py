"""
Autoimport Package: Watchfolders & kontinuierliche Bildanalyse

Module:
    - watchfolder_monitor: QFileSystemWatcher-Wrapper
    - debounced_event_handler: Debounce-Logik für Event-Batching
    - autoimport_pipeline: Analyse-Orchestrierung
    - autoimport_controller: Hauptkoordinator
"""

from .autoimport_controller import AutoimportController

__all__ = ['AutoimportController']
