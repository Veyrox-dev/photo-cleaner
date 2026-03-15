from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from photo_cleaner.ui.workflows.rating_workflow_controller import RatingWorkflowController


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _SignalStub:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback) -> None:
        self.callbacks.append(callback)


class _ThreadStub:
    def __init__(self) -> None:
        self.progress = _SignalStub()
        self.finished = _SignalStub()
        self.error = _SignalStub()
        self.started = False

    def start(self) -> None:
        self.started = True


class _DialogStub:
    def __init__(self, visible: bool) -> None:
        self._visible = visible
        self.show_called = False

    def isVisible(self) -> bool:
        return self._visible

    def show(self) -> None:
        self.show_called = True
        self._visible = True


def test_create_and_wire_rating_thread_connects_callbacks(qapp: QApplication) -> None:
    owner = QWidget()
    received = {}

    def _factory(db_path: Path, top_n: int, mtcnn_status: dict | None):
        received["db_path"] = db_path
        received["top_n"] = top_n
        received["mtcnn_status"] = mtcnn_status
        return _ThreadStub()

    controller = RatingWorkflowController(owner, _factory, lambda: None)

    thread = controller.create_and_wire_rating_thread(
        Path("C:/tmp/photo_cleaner.db"),
        3,
        {"available": True, "error": None},
        on_progress=lambda *_args: None,
        on_finished=lambda *_args: None,
        on_error=lambda *_args: None,
    )

    assert received["top_n"] == 3
    assert received["mtcnn_status"]["available"] is True
    assert len(thread.progress.callbacks) == 1
    assert len(thread.finished.callbacks) == 1
    assert len(thread.error.callbacks) == 1


def test_start_rating_thread_shows_hidden_dialog_and_processes_events() -> None:
    processed = {"called": False}
    thread = _ThreadStub()
    dialog = _DialogStub(visible=False)

    controller = RatingWorkflowController(QWidget(), lambda *_args: thread, lambda: processed.__setitem__("called", True))
    controller.start_rating_thread(thread, dialog)

    assert thread.started is True
    assert dialog.show_called is True
    assert processed["called"] is True


def test_start_rating_thread_keeps_visible_dialog_and_processes_events() -> None:
    processed = {"called": False}
    thread = _ThreadStub()
    dialog = _DialogStub(visible=True)

    controller = RatingWorkflowController(QWidget(), lambda *_args: thread, lambda: processed.__setitem__("called", True))
    controller.start_rating_thread(thread, dialog)

    assert thread.started is True
    assert dialog.show_called is False
    assert processed["called"] is True
