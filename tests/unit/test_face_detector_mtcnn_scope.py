import logging

from photo_cleaner.pipeline.analysis import face_detector as fd
from photo_cleaner.pipeline.analysis.face_detector import FaceDetector
from photo_cleaner.pipeline.analysis.models import FaceQuality


class _FakeImage:
    shape = (100, 100, 3)


def test_mtcnn_scope_does_not_raise_unboundlocal(monkeypatch, caplog) -> None:
    detector = FaceDetector()

    # Force fast fallback path that reads MTCNN_AVAILABLE.
    monkeypatch.setattr(fd, "MTCNN_AVAILABLE", False)

    # Avoid OpenCV or model dependencies in this regression test.
    monkeypatch.setattr(detector, "_analyze_faces_haar", lambda img: FaceQuality(has_face=False))

    caplog.set_level(logging.WARNING)
    result = detector._analyze_faces_mtcnn(_FakeImage())

    assert result.has_face is False
    assert "cannot access local variable 'MTCNN_AVAILABLE'" not in caplog.text
