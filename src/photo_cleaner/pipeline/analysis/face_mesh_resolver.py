from __future__ import annotations

import logging
import urllib.request

from photo_cleaner.config import AppConfig

logger = logging.getLogger(__name__)

_FACE_MESH_CTOR = None
_FACE_MESH_RESOLVED = False
_FACE_MESH_MODULE_ID = None


def resolve_face_mesh_ctor(*, mediapipe_available: bool, mp_module=None):
    """Resolve MediaPipe Face Mesh constructor from available shims once."""
    global _FACE_MESH_CTOR, _FACE_MESH_RESOLVED, _FACE_MESH_MODULE_ID

    current_module_id = id(mp_module) if mp_module is not None else None
    if _FACE_MESH_RESOLVED and _FACE_MESH_MODULE_ID == current_module_id:
        return _FACE_MESH_CTOR

    _FACE_MESH_CTOR = None
    _FACE_MESH_RESOLVED = True
    _FACE_MESH_MODULE_ID = current_module_id

    if not mediapipe_available or mp_module is None:
        return None

    try:
        if hasattr(mp_module, "solutions"):
            _FACE_MESH_CTOR = mp_module.solutions.face_mesh.FaceMesh
            return _FACE_MESH_CTOR
        try:
            from mediapipe import solutions as mp_solutions  # type: ignore

            _FACE_MESH_CTOR = mp_solutions.face_mesh.FaceMesh
            return _FACE_MESH_CTOR
        except (ImportError, AttributeError):
            try:
                from mediapipe.python import solutions as mp_py_solutions  # type: ignore

                _FACE_MESH_CTOR = mp_py_solutions.face_mesh.FaceMesh
                return _FACE_MESH_CTOR
            except ModuleNotFoundError as mnfe:
                if "mediapipe.python" not in str(mnfe):
                    raise

        try:
            import importlib

            vision = importlib.import_module("mediapipe.tasks.python.vision")
            core = importlib.import_module("mediapipe.tasks.python.core")
            image_module = importlib.import_module("mediapipe.tasks.python.vision.core.image")

            FaceLandmarker = getattr(vision, "FaceLandmarker")
            FaceLandmarkerOptions = getattr(vision, "FaceLandmarkerOptions")
            RunningMode = getattr(vision, "RunningMode")
            BaseOptions = getattr(core.base_options, "BaseOptions")
            Image = getattr(image_module, "Image")
            ImageFormat = getattr(image_module, "ImageFormat")

            def _ensure_face_landmarker_model() -> str:
                cache_dir = AppConfig.get_cache_dir() / "mediapipe"
                cache_dir.mkdir(parents=True, exist_ok=True)
                model_path = cache_dir / "face_landmarker.task"
                if model_path.exists():
                    return str(model_path)
                url = (
                    "https://storage.googleapis.com/mediapipe-models/"
                    "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
                )
                logger.info("Downloading MediaPipe face_landmarker model...")
                urllib.request.urlretrieve(url, model_path)  # noqa: S310
                return str(model_path)

            class _LandmarkList:
                def __init__(self, landmarks):
                    self.landmark = landmarks

            class _Result:
                def __init__(self, face_landmarks):
                    self.multi_face_landmarks = face_landmarks

            class _FaceMeshTasksWrapper:
                def __init__(self, *args, **kwargs):
                    model_path = _ensure_face_landmarker_model()
                    options = FaceLandmarkerOptions(
                        base_options=BaseOptions(model_asset_path=model_path),
                        running_mode=RunningMode.IMAGE,
                        num_faces=10,
                        min_face_detection_confidence=0.7,
                        min_face_presence_confidence=0.7,
                        min_tracking_confidence=0.7,
                    )
                    self._landmarker = FaceLandmarker.create_from_options(options)

                def process(self, rgb_image):
                    if rgb_image is None:
                        return _Result([])
                    mp_image = Image(image_format=ImageFormat.SRGB, data=rgb_image)
                    result = self._landmarker.detect(mp_image)
                    if not result or not getattr(result, "face_landmarks", None):
                        return _Result([])
                    wrapped = [_LandmarkList(lms) for lms in result.face_landmarks]
                    return _Result(wrapped)

                def close(self):
                    try:
                        self._landmarker.close()
                    except (RuntimeError, AttributeError):
                        logger.debug("Error closing landmarker", exc_info=True)

            _FACE_MESH_CTOR = _FaceMeshTasksWrapper
            return _FACE_MESH_CTOR
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            logger.debug(f"Face Mesh fallback failed: {e}", exc_info=True)
            return None
    except (ImportError, AttributeError, ValueError) as e:  # noqa: BLE001
        logger.debug(f"Face Mesh import error: {e}", exc_info=True)
        return None
