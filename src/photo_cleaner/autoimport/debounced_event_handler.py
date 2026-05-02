"""
DebouncedEventHandler: Debounce-Logik für Filesystem-Events.

Verantwortung:
    - Sammelt Events in Zwischenpuffer
    - Startet/resettet Timer
    - Emitiert gebündelte Events nach Debounce-Fenster
"""

import logging
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class DebouncedEventHandler(QObject):
    """
    Debounce-Handler für Filesystem-Events.
    
    Verhindert, dass viele Datei-Events in schneller Folge zu mehreren
    redundanten Analysen führen. Stattdessen werden alle Events innerhalb
    eines Fensters gebündelt und dann als eine analyse_requested emittiert.
    
    Beispiel:
        - Event 1 (photo1.jpg) → Timer startet (3000ms)
        - Event 2 (photo2.jpg) nach 500ms → Buffer erweitert, Timer resettet
        - Event 3 (photo3.jpg) nach 500ms → Buffer erweitert, Timer resettet
        - Nach 3000ms ohne neuer Events → analysis_requested([photo1, photo2, photo3])
    """
    
    # Signale
    analysis_requested = pyqtSignal(list)  # list of file paths (str)
    debounce_triggered = pyqtSignal()  # signal when debounce activates (optional, für Debugging)
    
    def __init__(self, debounce_ms: int = 3000):
        """
        Initialisiert den Debounce-Handler.
        
        Args:
            debounce_ms: Debounce-Fenster in Millisekunden (default: 3000ms)
        """
        super().__init__()
        self.debounce_ms = debounce_ms
        self._event_buffer = set()
        self._debounce_timer = QTimer()
        self._debounce_timer.timeout.connect(self._on_timer_expired)
        self._debounce_timer.setSingleShot(True)
        
        logger.debug(f"DebouncedEventHandler initialisiert (debounce: {debounce_ms}ms)")
    
    def handle_event(self, file_path: str):
        """
        Registriert ein neues Filesystem-Event.
        
        Fügt die Datei zum Event-Buffer hinzu und resettet den Debounce-Timer.
        
        Args:
            file_path: Pfad zur erkannten Datei (str)
        """
        self._event_buffer.add(file_path)
        
        # Timer stoppen und neu starten (kontinuierlicher Reset)
        if self._debounce_timer.isActive():
            self._debounce_timer.stop()
            logger.debug(f"DebouncedEventHandler: Timer resettet für neue Datei: {Path(file_path).name}")
        else:
            logger.debug(f"DebouncedEventHandler: Timer gestartet für neue Datei: {Path(file_path).name}")
        
        self._debounce_timer.start(self.debounce_ms)
    
    def _on_timer_expired(self):
        """
        Qt-Slot: Debounce-Fenster ist abgelaufen.
        
        Wird aufgerufen, wenn keine neuen Events mehr für debounce_ms ankommen.
        Emitiert analysis_requested mit allen gepufferten Dateien.
        """
        if not self._event_buffer:
            logger.debug("DebouncedEventHandler: Timer abgelaufen, Buffer ist leer")
            return
        
        # Kopiere Buffer und leere ihn
        files = list(self._event_buffer)
        self._event_buffer.clear()
        
        logger.debug(f"DebouncedEventHandler: Timer abgelaufen. {len(files)} Dateien im Buffer")
        
        # Filtere: Nur Dateien, die noch existieren
        # (verhindert Race Conditions, wenn Datei gelöscht wird bevor Analyse startet)
        existing = [f for f in files if Path(f).exists()]
        
        if len(existing) < len(files):
            logger.warning(f"DebouncedEventHandler: {len(files) - len(existing)} Dateien wurden gelöscht, "
                          f"bevor Analyse startete. Verarbeite nur {len(existing)} Dateien.")
        
        if existing:
            logger.info(f"DebouncedEventHandler: Emitiere analysis_requested für {len(existing)} Dateien")
            self.debounce_triggered.emit()
            self.analysis_requested.emit(existing)
        else:
            logger.debug("DebouncedEventHandler: Keine existierenden Dateien nach Filter, ignoriere")
    
    def set_debounce_window(self, ms: int):
        """
        Ändert das Debounce-Fenster zur Laufzeit.
        
        Args:
            ms: Neue Fensterbreite in Millisekunden
        """
        logger.info(f"DebouncedEventHandler: Debounce-Fenster geändert: {self.debounce_ms}ms → {ms}ms")
        self.debounce_ms = ms
    
    def get_debounce_window(self) -> int:
        """Gibt das aktuelle Debounce-Fenster zurück."""
        return self.debounce_ms
    
    def get_buffer_size(self) -> int:
        """Gibt die Anzahl gepufferter Events zurück (für Debugging/Logging)."""
        return len(self._event_buffer)
    
    def flush(self):
        """
        Verarbeitet gepufferte Events sofort.
        
        Nützlich für Shutdown oder Force-Triggers.
        Stoppt Timer und emitiert analysis_requested wenn Events vorhanden.
        """
        if self._debounce_timer.isActive():
            self._debounce_timer.stop()
            logger.info(f"DebouncedEventHandler: flush() aufgerufen, verarbeite {len(self._event_buffer)} Events sofort")
        
        self._on_timer_expired()
    
    def clear(self):
        """Leert den Event-Buffer und stoppt den Timer (keine Analyse)."""
        self._debounce_timer.stop()
        self._event_buffer.clear()
        logger.debug("DebouncedEventHandler: Buffer und Timer geleert")
