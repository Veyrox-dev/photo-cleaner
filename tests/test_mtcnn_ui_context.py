from photo_cleaner.pipeline import quality_analyzer as qa


def _reset_dep_state() -> None:
    qa._deps_initialized = False
    qa._cv2 = None
    qa._np = None
    qa._Image = None
    qa._mp = None
    qa._dlib = None
    qa._MTCNN = None
    qa.CV2_AVAILABLE = True
    qa.MEDIAPIPE_AVAILABLE = True
    qa.DLIB_AVAILABLE = True
    qa.MTCNN_AVAILABLE = True
    qa._MTCNN_IMPORT_ERROR = None


def test_mtcnn_ui_context_guard(monkeypatch):
    _reset_dep_state()
    monkeypatch.setenv("PHOTOCLEANER_SKIP_HEAVY_DEPS", "1")

    from PySide6.QtWidgets import QApplication
    from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer

    assert QApplication is not None

    analyzer = QualityAnalyzer(use_face_mesh=False)
    analyzer.warmup()

    _reset_dep_state()