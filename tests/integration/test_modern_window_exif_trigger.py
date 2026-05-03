"""UI workflow test: rating completion triggers EXIF grouping in ModernMainWindow."""

import sqlite3
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

from photo_cleaner.db.schema import Database
from photo_cleaner.ui.modern_window import ModernMainWindow


def test_rating_finished_triggers_exif_grouping_and_updates_db(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "ui_workflow.db"
        image_path = tmp_path / "keep_001.jpg"
        image_path.touch()

        db = Database(db_path)
        conn = db.connect()
        conn.execute(
            """
            INSERT INTO files (path, file_status, is_deleted)
            VALUES (?, ?, ?)
            """,
            (str(image_path), "KEEP", 0),
        )
        conn.commit()
        db.close()

        # Keep construction deterministic and headless-friendly.
        monkeypatch.setattr(ModernMainWindow, "_build_ui", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "show", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_setup_grid_thumbnail_loader", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_build_menu", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_wire_shortcuts", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_on_theme_changed", lambda self, _theme=None: None)
        monkeypatch.setattr(ModernMainWindow, "_load_session", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "refresh_groups", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_update_progress", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_setup_auto_save", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_maybe_show_first_run_onboarding", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_schedule_update_check", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_show_analysis_summary", lambda self, _summary: None)
        monkeypatch.setattr(ModernMainWindow, "_persist_analysis_metrics", lambda self, _info: None)
        monkeypatch.setattr(ModernMainWindow, "_open_review", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_show_gallery_review_badge", lambda self, _count: None)
        monkeypatch.setattr(ModernMainWindow, "_update_thumbnail_progress", lambda self: None)

        win = ModernMainWindow(db_path=db_path)
        # _build_ui is patched to no-op in this test; set expected attrs explicitly.
        win._group_thumb_loader = None
        win._grid_thumb_loader = None

        calls: dict[str, object] = {}

        def fake_group_images(paths, scan_session_id=None):
            calls["paths"] = paths
            calls["scan_session_id"] = scan_session_id
            conn2 = sqlite3.connect(str(db_path))
            try:
                for p in paths:
                    conn2.execute(
                        "UPDATE files SET exif_location_name = ? WHERE path = ?",
                        ("Berlin, Deutschland", str(p)),
                    )
                conn2.commit()
            finally:
                conn2.close()

        monkeypatch.setattr(win._exif_grouping_engine, "group_images", fake_group_images)

        try:
            win._on_rating_finished({"rated": True})

            assert "paths" in calls
            assert len(calls["paths"]) == 1

            conn3 = sqlite3.connect(str(db_path))
            location = conn3.execute(
                "SELECT exif_location_name FROM files WHERE path = ?",
                (str(image_path),),
            ).fetchone()[0]
            conn3.close()

            assert location == "Berlin, Deutschland"
        finally:
            win.close()
            win.db.close()


def test_finish_post_indexing_keeps_review_open(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ui_workflow.db"
        db = Database(db_path)
        db.close()

        monkeypatch.setattr(ModernMainWindow, "_build_ui", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "show", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_setup_grid_thumbnail_loader", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_build_menu", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_wire_shortcuts", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_on_theme_changed", lambda self, _theme=None: None)
        monkeypatch.setattr(ModernMainWindow, "_load_session", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "refresh_groups", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_update_progress", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_setup_auto_save", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_maybe_show_first_run_onboarding", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_schedule_update_check", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_show_analysis_summary", lambda self, _summary: None)
        monkeypatch.setattr(ModernMainWindow, "_persist_analysis_metrics", lambda self, _info: None)
        monkeypatch.setattr(ModernMainWindow, "_show_gallery_review_badge", lambda self, _count: None)
        monkeypatch.setattr(ModernMainWindow, "_update_thumbnail_progress", lambda self: None)

        transitions: list[str] = []
        monkeypatch.setattr(ModernMainWindow, "_open_review", lambda self: transitions.append("review"))
        monkeypatch.setattr(ModernMainWindow, "_open_gallery", lambda self: transitions.append("gallery"))

        win = ModernMainWindow(db_path=db_path)
        win._group_thumb_loader = None
        win._grid_thumb_loader = None
        win._post_indexing_cancelled = False
        win._thumb_loading_active = False
        win._pending_rating_summary = None
        win._pipeline_start_ts = 0.0
        win._post_indexing_group_count = 3

        monkeypatch.setattr(win, "_trigger_exif_grouping_for_keep_images", lambda: None)

        try:
            win._on_rating_finished({"rated": True})

            assert transitions[-1] == "review"
            assert "gallery" not in transitions
        finally:
            win.close()
            win.db.close()


def test_modern_window_starts_autoimport_controller(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ui_workflow.db"
        db = Database(db_path)
        db.close()

        monkeypatch.setattr(ModernMainWindow, "_build_ui", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "show", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_setup_grid_thumbnail_loader", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_build_menu", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_wire_shortcuts", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_on_theme_changed", lambda self, _theme=None: None)
        monkeypatch.setattr(ModernMainWindow, "_load_session", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "refresh_groups", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_update_progress", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_setup_auto_save", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_maybe_show_first_run_onboarding", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_schedule_update_check", lambda self: None)

        calls = {"startup": 0, "shutdown": 0}

        class SignalStub:
            def connect(self, _callback):
                return None

        class FakeController:
            def __init__(self, *args, **kwargs):
                self.status_changed = SignalStub()
                self.import_complete = SignalStub()

            def startup(self):
                calls["startup"] += 1

            def shutdown(self):
                calls["shutdown"] += 1

        monkeypatch.setattr("photo_cleaner.ui.modern_window.AutoimportController", FakeController)

        win = ModernMainWindow(db_path=db_path)
        win._group_thumb_loader = None
        win._grid_thumb_loader = None

        try:
            assert calls["startup"] == 1
        finally:
            win.close()
            win.db.close()
            assert calls["shutdown"] == 1


def test_autoimport_complete_refreshes_gallery_and_badge(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ui_workflow.db"
        db = Database(db_path)
        db.close()

        monkeypatch.setattr(ModernMainWindow, "_build_ui", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "show", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_setup_grid_thumbnail_loader", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_build_menu", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_wire_shortcuts", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_on_theme_changed", lambda self, _theme=None: None)
        monkeypatch.setattr(ModernMainWindow, "_load_session", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_update_progress", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_setup_auto_save", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_maybe_show_first_run_onboarding", lambda self: None)
        monkeypatch.setattr(ModernMainWindow, "_schedule_update_check", lambda self: None)

        class SignalStub:
            def connect(self, _callback):
                return None

        class FakeController:
            def __init__(self, *args, **kwargs):
                self.status_changed = SignalStub()
                self.import_complete = SignalStub()

            def startup(self):
                return None

            def shutdown(self):
                return None

        monkeypatch.setattr("photo_cleaner.ui.modern_window.AutoimportController", FakeController)

        calls = {"gallery": 0, "groups": 0, "badge": []}
        monkeypatch.setattr(
            ModernMainWindow,
            "_refresh_gallery_data",
            lambda self: calls.__setitem__("gallery", calls["gallery"] + 1),
        )
        monkeypatch.setattr(
            ModernMainWindow,
            "refresh_groups",
            lambda self: calls.__setitem__("groups", calls["groups"] + 1),
        )
        monkeypatch.setattr(
            ModernMainWindow,
            "_show_gallery_review_badge",
            lambda self, count: calls["badge"].append(count),
        )

        win = ModernMainWindow(db_path=db_path)
        win._group_thumb_loader = None
        win._grid_thumb_loader = None
        win._map_widget = None
        win.status_label = type("StatusStub", (), {"setText": lambda self, text: None})()
        calls["gallery"] = 0
        calls["groups"] = 0

        try:
            win._on_autoimport_complete({"total_files": 4, "duplicates_found": 2})

            assert calls["gallery"] == 1
            assert calls["groups"] == 1
            assert calls["badge"] == [2]
        finally:
            win.close()
            win.db.close()