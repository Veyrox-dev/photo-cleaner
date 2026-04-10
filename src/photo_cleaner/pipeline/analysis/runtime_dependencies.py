"""Runtime dependency bootstrap for quality analysis pipeline.

Centralizes lazy imports and availability flags for heavy optional dependencies
(OpenCV, MediaPipe, dlib, MTCNN) with thread-safe one-time initialization.
"""
from __future__ import annotations

import importlib.util
import os
import queue
import sys
import threading
import types
from dataclasses import dataclass
from typing import Any


# Lazy-loaded modules/classes
_cv2 = None
_np = None
_Image = None
_mp = None
_dlib = None
_MTCNN = None

# Availability flags
CV2_AVAILABLE = True
MEDIAPIPE_AVAILABLE = True
DLIB_AVAILABLE = True
MTCNN_AVAILABLE = True

# Error state
_MTCNN_IMPORT_ERROR = None
_MEDIAPIPE_IMPORT_ERROR = None
_MEDIAPIPE_DRAWING_DISABLED = False

# Thread-safe one-time init
_deps_lock = threading.Lock()
_deps_initialized = False


@dataclass(frozen=True)
class RuntimeDependencySnapshot:
    """Immutable snapshot of runtime dependency state."""

    cv2_module: Any
    np_module: Any
    image_module: Any
    mp_module: Any
    dlib_module: Any
    mtcnn_class: Any
    cv2_available: bool
    mediapipe_available: bool
    dlib_available: bool
    mtcnn_available: bool
    mtcnn_import_error: str | None
    mediapipe_import_error: str | None
    mediapipe_drawing_disabled: bool


def _install_mediapipe_drawing_stubs() -> bool:
    """Provide stub drawing modules so MediaPipe core can load without matplotlib."""
    if importlib.util.find_spec("matplotlib") is not None:
        return False

    installed = False
    for module_name in (
        "mediapipe.tasks.python.vision.drawing_utils",
        "mediapipe.tasks.python.vision.drawing_styles",
    ):
        if module_name in sys.modules:
            continue
        stub = types.ModuleType(module_name)
        stub.__all__ = []
        sys.modules[module_name] = stub
        installed = True

    return installed


def get_runtime_dependency_snapshot() -> RuntimeDependencySnapshot:
    """Return a snapshot of current dependency state."""
    return RuntimeDependencySnapshot(
        cv2_module=_cv2,
        np_module=_np,
        image_module=_Image,
        mp_module=_mp,
        dlib_module=_dlib,
        mtcnn_class=_MTCNN,
        cv2_available=CV2_AVAILABLE,
        mediapipe_available=MEDIAPIPE_AVAILABLE,
        dlib_available=DLIB_AVAILABLE,
        mtcnn_available=MTCNN_AVAILABLE,
        mtcnn_import_error=_MTCNN_IMPORT_ERROR,
        mediapipe_import_error=_MEDIAPIPE_IMPORT_ERROR,
        mediapipe_drawing_disabled=_MEDIAPIPE_DRAWING_DISABLED,
    )


def mark_mtcnn_unavailable(reason: str) -> None:
    """Mark MTCNN unavailable after runtime initialization/warmup failure."""
    global MTCNN_AVAILABLE, _MTCNN_IMPORT_ERROR
    MTCNN_AVAILABLE = False
    _MTCNN_IMPORT_ERROR = reason


def ensure_runtime_dependencies(logger) -> RuntimeDependencySnapshot:
    """Initialize heavy dependencies once using double-check locking."""
    global _cv2, _np, _Image, _mp, _dlib, _MTCNN
    global CV2_AVAILABLE, MEDIAPIPE_AVAILABLE, DLIB_AVAILABLE, MTCNN_AVAILABLE
    global _MTCNN_IMPORT_ERROR, _MEDIAPIPE_IMPORT_ERROR, _MEDIAPIPE_DRAWING_DISABLED
    global _deps_initialized

    if _deps_initialized:
        return get_runtime_dependency_snapshot()

    skip_heavy = os.environ.get("PHOTOCLEANER_SKIP_HEAVY_DEPS") == "1"

    with _deps_lock:
        if _deps_initialized:
            return get_runtime_dependency_snapshot()

        try:
            import cv2 as cv2_module
            import numpy as np_module
            from PIL import Image as image_module

            _cv2 = cv2_module
            _np = np_module
            _Image = image_module
            CV2_AVAILABLE = True
        except ImportError as error:
            CV2_AVAILABLE = False
            logger.warning("OpenCV not available: %s", error)

        if skip_heavy:
            MEDIAPIPE_AVAILABLE = False
            logger.info("Skipping MediaPipe import due to PHOTOCLEANER_SKIP_HEAVY_DEPS=1")
        else:
            result_queue: queue.Queue[tuple[str, Any, bool]] = queue.Queue()

            def _import_mediapipe() -> None:
                try:
                    drawing_disabled = _install_mediapipe_drawing_stubs()
                    import mediapipe as mp_module

                    result_queue.put(("success", mp_module, drawing_disabled))
                except Exception as error:
                    # Catch all import failures (including KeyError) so the parent
                    # thread always receives a deterministic result.
                    result_queue.put(("error", error, False))

            import_thread = threading.Thread(target=_import_mediapipe, daemon=True)
            import_thread.start()
            import_thread.join(timeout=10.0)

            if import_thread.is_alive():
                MEDIAPIPE_AVAILABLE = False
                _MEDIAPIPE_IMPORT_ERROR = (
                    "Import timeout (>10s) - likely GPU enumeration hang in frozen build"
                )
                _MEDIAPIPE_DRAWING_DISABLED = False
                logger.warning(
                    "MediaPipe import timed out after 10s. "
                    "Skipping MediaPipe, using MTCNN/Haar fallbacks."
                )
            else:
                try:
                    status, result, drawing_disabled = result_queue.get_nowait()
                    if status == "success":
                        _mp = result
                        MEDIAPIPE_AVAILABLE = True
                        _MEDIAPIPE_IMPORT_ERROR = None
                        _MEDIAPIPE_DRAWING_DISABLED = drawing_disabled
                    else:
                        MEDIAPIPE_AVAILABLE = False
                        _MEDIAPIPE_IMPORT_ERROR = f"{type(result).__name__}: {result}"
                        _MEDIAPIPE_DRAWING_DISABLED = False
                        logger.warning("MediaPipe not available: %s", _MEDIAPIPE_IMPORT_ERROR)
                except queue.Empty:
                    MEDIAPIPE_AVAILABLE = False
                    _MEDIAPIPE_IMPORT_ERROR = "Import thread finished without result"
                    _MEDIAPIPE_DRAWING_DISABLED = False
                    logger.warning("MediaPipe not available: %s", _MEDIAPIPE_IMPORT_ERROR)

        if skip_heavy:
            DLIB_AVAILABLE = False
        else:
            try:
                import dlib as dlib_module  # type: ignore[import-not-found]

                _dlib = dlib_module
                DLIB_AVAILABLE = True
            except ImportError:
                DLIB_AVAILABLE = False

        face_detector = os.environ.get("PHOTOCLEANER_FACE_DETECTOR", "mtcnn").lower()
        if skip_heavy or face_detector != "mtcnn":
            MTCNN_AVAILABLE = False
            if skip_heavy:
                _MTCNN_IMPORT_ERROR = "Skipped by PHOTOCLEANER_SKIP_HEAVY_DEPS"
                logger.info("Skipping MTCNN import due to PHOTOCLEANER_SKIP_HEAVY_DEPS=1")
            else:
                _MTCNN_IMPORT_ERROR = (
                    f"Disabled via PHOTOCLEANER_FACE_DETECTOR={face_detector}"
                )
                logger.info("Skipping MTCNN import due to PHOTOCLEANER_FACE_DETECTOR setting")
        else:
            try:
                from mtcnn import MTCNN as mtcnn_class

                _MTCNN = mtcnn_class
                MTCNN_AVAILABLE = True
                _MTCNN_IMPORT_ERROR = None
            except (ImportError, RuntimeError, AttributeError, ValueError, OSError, Exception) as error:
                MTCNN_AVAILABLE = False
                _MTCNN_IMPORT_ERROR = f"Exception: {error}"
                if "DLL" in str(error) or "tensorflow" in str(error).lower():
                    logger.warning(
                        "MTCNN unavailable (TensorFlow DLL issue): %s. "
                        "Falling back to Haar Cascade.",
                        type(error).__name__,
                    )
                else:
                    logger.debug("MTCNN initialization error: %s", error, exc_info=True)

        _deps_initialized = True

    return get_runtime_dependency_snapshot()
