import pytest


@pytest.fixture(autouse=True)
def _test_env_defaults(monkeypatch):
    monkeypatch.setenv("PHOTOCLEANER_FACE_DETECTOR", "haar")
    monkeypatch.setenv("PHOTOCLEANER_EYE_DETECTION_STAGE", "1")
    monkeypatch.setenv("PHOTOCLEANER_SKIP_HEAVY_DEPS", "1")
    monkeypatch.setenv("TF_CPP_MIN_LOG_LEVEL", "3")
