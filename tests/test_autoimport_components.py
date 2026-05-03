"""
Unit-Tests für Autoimport-Komponenten.

Führe aus mit:
    pytest tests/test_autoimport_components.py -v
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtCore import QTimer, QCoreApplication

from src.photo_cleaner.autoimport.watchfolder_monitor import WatchfolderMonitor
from src.photo_cleaner.autoimport.debounced_event_handler import DebouncedEventHandler
from src.photo_cleaner.autoimport.autoimport_pipeline import AutoimportPipeline
from src.photo_cleaner.autoimport.autoimport_controller import AutoimportController


class TestWatchfolderMonitor:
    """Unit-Tests für WatchfolderMonitor."""
    
    def test_add_watchfolder_valid_path(self, tmp_path):
        """Test: Gültiger Ordner wird registriert."""
        monitor = WatchfolderMonitor()
        result = monitor.add_watchfolder(tmp_path, "Test")
        
        assert result is True
        assert str(tmp_path) in monitor.get_watched_paths()
        assert monitor.get_label(tmp_path) == "Test"
    
    def test_add_watchfolder_invalid_path(self):
        """Test: Ungültiger Ordner wird abgelehnt."""
        monitor = WatchfolderMonitor()
        result = monitor.add_watchfolder(Path("/nonexistent/path/that/does/not/exist"), "Test")
        
        assert result is False
    
    def test_add_watchfolder_path_object(self, tmp_path):
        """Test: Path-Objekt wird akzeptiert."""
        monitor = WatchfolderMonitor()
        result = monitor.add_watchfolder(tmp_path)
        
        assert result is True
    
    def test_add_watchfolder_string_path(self, tmp_path):
        """Test: String-Pfad wird zu Path konvertiert."""
        monitor = WatchfolderMonitor()
        result = monitor.add_watchfolder(str(tmp_path), "Test")
        
        assert result is True
    
    def test_remove_watchfolder(self, tmp_path):
        """Test: Watchfolder wird deregistriert."""
        monitor = WatchfolderMonitor()
        monitor.add_watchfolder(tmp_path, "Test")
        assert len(monitor.get_watched_paths()) == 1
        
        result = monitor.remove_watchfolder(tmp_path)
        assert result is True
        assert len(monitor.get_watched_paths()) == 0
    
    def test_get_watched_paths(self, tmp_path):
        """Test: get_watched_paths gibt alle Ordner zurück."""
        monitor = WatchfolderMonitor()
        folder1 = tmp_path / "folder1"
        folder2 = tmp_path / "folder2"
        folder1.mkdir()
        folder2.mkdir()
        
        monitor.add_watchfolder(folder1, "Folder 1")
        monitor.add_watchfolder(folder2, "Folder 2")
        
        paths = monitor.get_watched_paths()
        assert len(paths) == 2
        assert str(folder1) in paths
        assert str(folder2) in paths
    
    def test_is_watching(self, tmp_path):
        """Test: is_watching prüft korrekt."""
        monitor = WatchfolderMonitor()
        monitor.add_watchfolder(tmp_path, "Test")
        
        assert monitor.is_watching(tmp_path) is True
        assert monitor.is_watching(tmp_path / "nonexistent") is False
    
    def test_is_image_valid_formats(self):
        """Test: Bildformate werden erkannt."""
        test_cases = [
            (Path("photo.jpg"), True),
            (Path("image.png"), True),
            (Path("picture.raw"), True),
            (Path("document.pdf"), False),
            (Path("video.mp4"), False),
        ]
        
        for path, expected in test_cases:
            assert WatchfolderMonitor._is_image(path) == expected


class TestDebouncedEventHandler:
    """Unit-Tests für DebouncedEventHandler."""
    
    def test_initialization(self):
        """Test: Handler wird korrekt initialisiert."""
        handler = DebouncedEventHandler(debounce_ms=2000)
        
        assert handler.debounce_ms == 2000
        assert handler.get_buffer_size() == 0
    
    def test_handle_event_single(self, qtbot):
        """Test: Ein Event triggert nach Debounce-Fenster."""
        handler = DebouncedEventHandler(debounce_ms=100)
        
        with qtbot.waitSignal(handler.analysis_requested, timeout=500):
            handler.handle_event("/test/photo1.jpg")
    
    def test_handle_event_multiple_batched(self, qtbot):
        """Test: Mehrere Events werden zu einem Batch zusammengefasst."""
        handler = DebouncedEventHandler(debounce_ms=100)
        
        # Emitiere 5 Events schnell hintereinander und warte auf ein gebündeltes Signal.
        with qtbot.waitSignal(handler.analysis_requested, timeout=500) as blocker:
            for i in range(5):
                handler.handle_event(f"/test/photo{i}.jpg")

        emitted_files = blocker.args[0]
        assert len(emitted_files) == 5
    
    def test_timer_reset_on_event(self, qtbot):
        """Test: Timer wird bei neuem Event resettet."""
        handler = DebouncedEventHandler(debounce_ms=100)
        
        # Erste Datei
        handler.handle_event("/test/photo1.jpg")
        assert handler.get_buffer_size() == 1
        
        # Nach 50ms: zweite Datei (Timer resettet)
        QTimer.singleShot(50, lambda: handler.handle_event("/test/photo2.jpg"))
        
        # Sollte nach ~150ms insgesamt (100ms + 100ms) emitieren
        with qtbot.waitSignal(handler.analysis_requested, timeout=300):
            pass
        
        # Nach emit sollte buffer leer sein
        assert handler.get_buffer_size() == 0
    
    def test_set_debounce_window(self):
        """Test: Debounce-Fenster kann zur Laufzeit geändert werden."""
        handler = DebouncedEventHandler(debounce_ms=2000)
        assert handler.get_debounce_window() == 2000
        
        handler.set_debounce_window(5000)
        assert handler.get_debounce_window() == 5000
    
    def test_flush_with_events(self, qtbot):
        """Test: flush() verarbeitet Events sofort."""
        handler = DebouncedEventHandler(debounce_ms=3000)
        
        handler.handle_event("/test/photo1.jpg")
        handler.handle_event("/test/photo2.jpg")
        
        assert handler.get_buffer_size() == 2
        
        with qtbot.waitSignal(handler.analysis_requested, timeout=100):
            handler.flush()
        
        assert handler.get_buffer_size() == 0
    
    def test_flush_without_events(self):
        """Test: flush() mit leerem Buffer emitiert nichts."""
        handler = DebouncedEventHandler(debounce_ms=2000)
        
        # Sollte keine Exception werfen
        handler.flush()
        
        assert handler.get_buffer_size() == 0
    
    def test_clear(self):
        """Test: clear() leert Buffer und Timer."""
        handler = DebouncedEventHandler(debounce_ms=2000)
        
        handler.handle_event("/test/photo1.jpg")
        assert handler.get_buffer_size() == 1
        
        handler.clear()
        assert handler.get_buffer_size() == 0


class TestAutoimportPipeline:
    """Unit-Tests für AutoimportPipeline."""
    
    @pytest.fixture
    def pipeline(self, tmp_path):
        """Erstelle Test-Pipeline."""
        db_path = tmp_path / "test.db"
        config_mock = Mock()
        license_mock = Mock()
        
        return AutoimportPipeline(db_path, config_mock, license_mock)
    
    def test_is_supported_format(self, pipeline):
        """Test: Bildformate werden erkannt."""
        test_cases = [
            (Path("photo.jpg"), True),
            (Path("image.png"), True),
            (Path("picture.raw"), True),
            (Path("document.pdf"), False),
        ]
        
        for path, expected in test_cases:
            assert pipeline._is_supported_format(path) == expected
    
    def test_is_running_initially_false(self, pipeline):
        """Test: Pipeline ist anfangs nicht laufend."""
        assert pipeline.is_running() is False
    
    def test_analyze_files_empty_list(self, pipeline):
        """Test: Leere Dateiliste wird ignoriert."""
        # Sollte keine Exception werfen
        pipeline.analyze_files([])


class TestAutoimportController:
    """Unit-Tests für AutoimportController."""
    
    @pytest.fixture
    def controller(self, tmp_path):
        """Erstelle Test-Controller."""
        db_path = tmp_path / "test.db"
        config_mock = Mock()
        config_mock.autoimport_enabled = True
        
        license_mock = Mock()
        license_mock.license_type = "FREE"
        
        controller = AutoimportController(
            db_path=db_path,
            config=config_mock,
            license_manager=license_mock
        )
        
        # Überschreibe Config-Dateipfad
        controller.CONFIG_FILE = tmp_path / "watchfolders.json"
        
        return controller, tmp_path
    
    def test_add_watchfolder(self, controller):
        """Test: Watchfolder hinzufügen."""
        ctrl, tmp_path = controller
        test_folder = tmp_path / "photos"
        test_folder.mkdir()
        
        result = ctrl.add_watchfolder(test_folder, "Meine Fotos")
        
        assert result is True
        watchfolders = ctrl.get_watchfolders()
        assert len(watchfolders) >= 1
    
    def test_remove_watchfolder(self, controller):
        """Test: Watchfolder entfernen."""
        ctrl, tmp_path = controller
        test_folder = tmp_path / "photos"
        test_folder.mkdir()
        
        ctrl.add_watchfolder(test_folder, "Meine Fotos")
        initial_count = len(ctrl.get_watchfolders())
        
        result = ctrl.remove_watchfolder(test_folder)
        
        assert result is True
        assert len(ctrl.get_watchfolders()) == initial_count - 1
    
    def test_get_watchfolders(self, controller):
        """Test: get_watchfolders gibt korrekte Struktur zurück."""
        ctrl, tmp_path = controller
        test_folder1 = tmp_path / "photos1"
        test_folder2 = tmp_path / "photos2"
        test_folder1.mkdir()
        test_folder2.mkdir()
        
        ctrl.add_watchfolder(test_folder1, "Urlaub")
        ctrl.add_watchfolder(test_folder2, "Familie")
        
        watchfolders = ctrl.get_watchfolders()
        
        assert len(watchfolders) >= 2
        for wf in watchfolders:
            assert "path" in wf
            assert "label" in wf
            assert isinstance(wf["path"], str)
            assert isinstance(wf["label"], str)
    
    def test_set_debounce_window(self, controller):
        """Test: Debounce-Fenster kann geändert werden."""
        ctrl, _ = controller
        
        ctrl.set_debounce_window(5000)
        assert ctrl._debouncer.get_debounce_window() == 5000
    
    def test_is_enabled_initially_false(self, controller):
        """Test: Controller ist anfangs nicht aktiv."""
        ctrl, _ = controller
        assert ctrl.is_enabled() is False
    
    def test_is_analyzing_initially_false(self, controller):
        """Test: Pipeline ist anfangs nicht laufend."""
        ctrl, _ = controller
        assert ctrl.is_analyzing() is False
    
    def test_persistence_save_watchfolders(self, controller):
        """Test: Watchfolders werden persistent gespeichert."""
        ctrl, tmp_path = controller
        test_folder = tmp_path / "photos"
        test_folder.mkdir()
        
        ctrl.add_watchfolder(test_folder, "Meine Fotos")
        
        # Prüfe ob Config-Datei erstellt wurde
        assert ctrl.CONFIG_FILE.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
