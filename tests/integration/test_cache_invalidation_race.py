"""
TEST-4: Cache Invalidation Race-Condition Tests

Ensures thread-safe invalidation of MediaPipe Face Mesh cache.
Verifies _invalidate_face_mesh_cache() can be called concurrently without errors.
"""

import threading

from photo_cleaner.pipeline import quality_analyzer as qa


class DummyFaceMeshCache:
    """Dummy face mesh cache object to track close calls."""

    def __init__(self):
        self.closed = False
        self.close_count = 0
        self._lock = threading.Lock()

    def close(self):
        with self._lock:
            if self.closed:
                raise RuntimeError("Cache closed twice")
            self.closed = True
            self.close_count += 1


def test_cache_invalidation_thread_safe(monkeypatch):
    monkeypatch.setenv("PHOTOCLEANER_SKIP_HEAVY_DEPS", "1")
    from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
    analyzer = QualityAnalyzer(use_face_mesh=False)

    # Ensure lock exists even if MediaPipe is unavailable
    if not hasattr(analyzer, "_cache_lock"):
        analyzer._cache_lock = threading.Lock()

    dummy_cache = DummyFaceMeshCache()
    analyzer._face_mesh_cache = dummy_cache

    start_barrier = threading.Barrier(5)

    def worker():
        start_barrier.wait()
        analyzer._invalidate_face_mesh_cache()

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert dummy_cache.close_count == 1
    assert analyzer._face_mesh_cache is None

    qa._deps_initialized = False
    qa.CV2_AVAILABLE = True
    qa.MEDIAPIPE_AVAILABLE = True
    qa.DLIB_AVAILABLE = True
    qa.MTCNN_AVAILABLE = True
    qa._MTCNN_IMPORT_ERROR = None
