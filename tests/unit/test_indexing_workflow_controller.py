from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from photo_cleaner.ui.workflows import indexing_workflow_controller as workflow_module
from photo_cleaner.ui.workflows.indexing_workflow_controller import IndexingWorkflowController


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_create_indexing_progress_dialog_applies_defaults(qapp: QApplication) -> None:
    owner = QWidget()
    centered = {"called": False}

    def _center(_dialog) -> None:
        centered["called"] = True

    controller = IndexingWorkflowController(owner, _center)
    dialog = controller.create_indexing_progress_dialog()

    assert dialog.minimumWidth() == 460
    assert dialog.minimumHeight() == 140
    assert dialog.value() == 0
    assert centered["called"] is True


def test_create_post_indexing_progress_dialog_wires_cancel(qapp: QApplication) -> None:
    owner = QWidget()
    centered = {"called": False}
    cancelled = {"called": False}

    def _center(_dialog) -> None:
        centered["called"] = True

    def _on_cancel() -> None:
        cancelled["called"] = True

    controller = IndexingWorkflowController(owner, _center)
    dialog = controller.create_post_indexing_progress_dialog(on_cancel=_on_cancel)
    dialog.canceled.emit()

    assert centered["called"] is True
    assert cancelled["called"] is True


def test_create_indexing_thread_connects_callbacks(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _SignalStub:
        def __init__(self) -> None:
            self.callbacks = []

        def connect(self, callback) -> None:
            self.callbacks.append(callback)

    class _FakeThread:
        def __init__(self, folder_path: Path, indexer, use_incremental: bool = True) -> None:
            self.folder_path = folder_path
            self.indexer = indexer
            self.use_incremental = use_incremental
            self.progress = _SignalStub()
            self.finished = _SignalStub()
            self.error = _SignalStub()

    monkeypatch.setattr(workflow_module, "IndexingThread", _FakeThread)

    owner = QWidget()
    controller = IndexingWorkflowController(owner, lambda _dialog: None)

    thread = controller.create_indexing_thread(
        Path("C:/tmp/photos"),
        object(),
        on_progress=lambda *_args: None,
        on_finished=lambda *_args: None,
        on_error=lambda *_args: None,
    )

    assert thread.use_incremental is True
    assert len(thread.progress.callbacks) == 1
    assert len(thread.finished.callbacks) == 1
    assert len(thread.error.callbacks) == 1
