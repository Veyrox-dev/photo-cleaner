"""
Quality Analyzer with MTCNN + MediaPipe

Expensive quality analysis for duplicate groups.

PHASE 2026: Modern face detection using MTCNN
- MTCNN: Accurate face detection (replaces Haar Cascade, 90% fewer false positives)
- MediaPipe Face Mesh: Eye analysis on validated MTCNN faces
- Combined approach: Best accuracy for multi-person group photos

Detection stages:
- Stage 1: MTCNN + MediaPipe (default, modern)
- Fallback: Haar Cascade + MediaPipe (legacy, ENV: PHOTOCLEANER_FACE_DETECTOR=haar)

Uses MediaPipe Face Mesh to detect:
- Eyes open/closed (all persons must have eyes open)
- Gaze direction
- Head orientation
- Fine-grained sharpness per face

Graceful fallback if dependencies unavailable:
- Still analyzes sharpness, resolution, lighting
- Face quality returns neutral scores
- No crash, application continues

Logging:
- DEBUG mode: Detailed analysis for each image
- RELEASE mode: Only warnings/errors for critical issues
"""
from __future__ import annotations

import importlib.util
import logging
import os
import sys
import threading
import types
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
else:
    NDArray = object

# Register HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # pillow-heif not available

# LAZY IMPORTS - Only import on first use to avoid PyInstaller frozen module issues
_cv2 = None
_np = None
_Image = None
_mp = None
_dlib = None
_MTCNN = None

# P1 FIX #5: Thread-safe dependency initialization
_deps_lock = threading.Lock()
_deps_initialized = False

CV2_AVAILABLE = True  # Assume available, check on first use
MEDIAPIPE_AVAILABLE = True
DLIB_AVAILABLE = True
MTCNN_AVAILABLE = True
_MTCNN_IMPORT_ERROR = None
_MTCNN_WARNING_LOGGED = False  # Flag to log MTCNN warning only once
_MEDIAPIPE_IMPORT_ERROR = None
_MEDIAPIPE_DRAWING_DISABLED = False

# Cache MediaPipe Face Mesh constructor resolution to avoid repeated import attempts
_FACE_MESH_CTOR = None
_FACE_MESH_IMPORT_ERROR = None
_FACE_MESH_RESOLVED = False
_FACE_MESH_WARNED = False


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

def _ensure_dependencies():
    """P1 FIX #5: Thread-safe lazy initialization of all heavy dependencies.
    
    Uses double-check locking pattern:
    - First check: fast path without lock (if already initialized)
    - Acquire lock: only if need to initialize
    - Second check: verify not initialized by another thread
    - Initialize: all imports protected by lock
    """
    global _cv2, _np, _Image, _mp, _dlib, _MTCNN
    global CV2_AVAILABLE, MEDIAPIPE_AVAILABLE, DLIB_AVAILABLE, MTCNN_AVAILABLE, _MTCNN_IMPORT_ERROR
    global _MEDIAPIPE_IMPORT_ERROR, _MEDIAPIPE_DRAWING_DISABLED
    global cv2, np, Image, MTCNN  # Also set unprefixed versions for backward compatibility
    global _deps_initialized
    
    logger.debug("[DEPS] _ensure_dependencies called")
    
    # Fast path: already initialized
    if _deps_initialized:
        logger.debug("[DEPS] Already initialized, returning")
        return
    skip_heavy = os.environ.get("PHOTOCLEANER_SKIP_HEAVY_DEPS") == "1"
    logger.debug(f"[DEPS] skip_heavy={skip_heavy}")
    
    # P1 FIX #5: Acquire lock to prevent multiple threads from importing simultaneously
    logger.debug("[DEPS] Acquiring lock...")
    with _deps_lock:
        logger.debug("[DEPS] Lock acquired")
        # Check again in case another thread initialized while we waited for lock
        if _deps_initialized:
            logger.debug("[DEPS] Initialized by another thread, returning")
            return
        
        # Import cv2 and numpy
        logger.debug("[DEPS] Importing cv2, numpy, PIL...")
        try:
            import cv2 as cv2_module
            import numpy as np_module
            from PIL import Image as Image_module
            _cv2 = cv2_module
            _np = np_module
            _Image = Image_module
            cv2 = cv2_module  # Also set unprefixed for backward compatibility
            np = np_module
            Image = Image_module
            CV2_AVAILABLE = True
            logger.debug("[DEPS] cv2, numpy, PIL imported successfully")
        except ImportError as e:
            CV2_AVAILABLE = False
            logger.warning(f"OpenCV not available: {e}")
        
        # Import mediapipe with timeout protection (blocks ~30s in frozen builds)
        logger.debug("[DEPS] Checking MediaPipe...")
        if skip_heavy:
            MEDIAPIPE_AVAILABLE = False
            logger.info("Skipping MediaPipe import due to PHOTOCLEANER_SKIP_HEAVY_DEPS=1")
        else:
            import queue
            result_queue = queue.Queue()
            
            def _import_mediapipe():
                """Import MediaPipe in separate thread (can block 30s in frozen builds)."""
                try:
                    logger.debug("[DEPS-THREAD] Installing mediapipe drawing stubs...")
                    drawing_disabled = _install_mediapipe_drawing_stubs()
                    logger.debug("[DEPS-THREAD] Importing mediapipe...")
                    import mediapipe as mp_module
                    result_queue.put(("success", mp_module, drawing_disabled))
                except (ImportError, OSError, RuntimeError, AttributeError) as e:
                    result_queue.put(("error", e, False))
            
            logger.debug("[DEPS] Starting MediaPipe import thread (10s timeout)...")
            import_thread = threading.Thread(target=_import_mediapipe, daemon=True)
            import_thread.start()
            import_thread.join(timeout=10.0)
            
            if import_thread.is_alive():
                # Timeout - MediaPipe import is hanging
                MEDIAPIPE_AVAILABLE = False
                _MEDIAPIPE_IMPORT_ERROR = "Import timeout (>10s) - likely GPU enumeration hang in frozen build"
                _MEDIAPIPE_DRAWING_DISABLED = False
                logger.warning(
                    "[DEPS] MediaPipe import timed out after 10s (frozen build GPU check hang). "
                    "Skipping MediaPipe, using MTCNN only."
                )
            else:
                # Import completed within timeout
                try:
                    status, result, drawing_disabled = result_queue.get_nowait()
                    if status == "success":
                        _mp = result
                        MEDIAPIPE_AVAILABLE = True
                        _MEDIAPIPE_IMPORT_ERROR = None
                        _MEDIAPIPE_DRAWING_DISABLED = drawing_disabled
                        logger.debug("[DEPS] MediaPipe imported successfully")
                        if _MEDIAPIPE_DRAWING_DISABLED:
                            logger.debug(
                                "MediaPipe core available (drawing disabled: matplotlib not installed)"
                            )
                    else:
                        MEDIAPIPE_AVAILABLE = False
                        _MEDIAPIPE_IMPORT_ERROR = f"{type(result).__name__}: {result}"
                        _MEDIAPIPE_DRAWING_DISABLED = False
                        logger.warning(f"MediaPipe not available: {_MEDIAPIPE_IMPORT_ERROR}")
                        logger.debug("MediaPipe import error details:", exc_info=True)
                except queue.Empty:
                    # Thread finished but no result (shouldn't happen)
                    MEDIAPIPE_AVAILABLE = False
                    _MEDIAPIPE_IMPORT_ERROR = "Import thread finished without result"
                    _MEDIAPIPE_DRAWING_DISABLED = False
                    logger.warning(f"MediaPipe not available: {_MEDIAPIPE_IMPORT_ERROR}")
        
        # Import dlib (optional)
        logger.debug("[DEPS] Checking dlib...")
        if skip_heavy:
            DLIB_AVAILABLE = False
        else:
            try:
                logger.debug("[DEPS] Importing dlib...")
                import dlib  # type: ignore[import-not-found]
                _dlib = dlib
                DLIB_AVAILABLE = True
                logger.debug("[DEPS] dlib imported successfully")
            except ImportError:
                DLIB_AVAILABLE = False
                logger.debug("[DEPS] dlib not available")
        
        # Import MTCNN
        logger.debug("[DEPS] Checking MTCNN...")
        face_detector = os.environ.get("PHOTOCLEANER_FACE_DETECTOR", "mtcnn").lower()
        if skip_heavy or face_detector != "mtcnn":
            MTCNN_AVAILABLE = False
            if skip_heavy:
                _MTCNN_IMPORT_ERROR = "Skipped by PHOTOCLEANER_SKIP_HEAVY_DEPS"
                logger.info("Skipping MTCNN import due to PHOTOCLEANER_SKIP_HEAVY_DEPS=1")
            else:
                _MTCNN_IMPORT_ERROR = f"Disabled via PHOTOCLEANER_FACE_DETECTOR={face_detector}"
                logger.info("Skipping MTCNN import due to PHOTOCLEANER_FACE_DETECTOR setting")
        else:
            try:
                logger.debug("[DEPS] Importing MTCNN (TensorFlow)...")
                from mtcnn import MTCNN as MTCNN_class
                _MTCNN = MTCNN_class
                MTCNN = MTCNN_class  # Also set unprefixed for backward compatibility
                MTCNN_AVAILABLE = True
                _MTCNN_IMPORT_ERROR = None
                logger.debug("[DEPS] MTCNN imported successfully")
            except (ImportError, RuntimeError, AttributeError, ValueError, OSError, Exception) as e:
                # OSError catches DLL load failures, Exception catches TensorFlow initialization errors
                MTCNN_AVAILABLE = False
                _MTCNN_IMPORT_ERROR = f"Exception: {e}"
                logger.debug(f"[DEPS] MTCNN import failed: {e}")
                # Log warning only once, not for every image
                if "DLL" in str(e) or "tensorflow" in str(e).lower():
                    logger.warning(f"MTCNN unavailable (TensorFlow DLL issue): {type(e).__name__}. Falling back to Haar Cascade.")
                else:
                    logger.debug(f"MTCNN initialization error: {e}", exc_info=True)
        
        # P1 FIX #5: Mark initialization complete LAST
        # This signals to other threads that imports are ready
        logger.debug("[DEPS] All imports complete, setting _deps_initialized=True")
        _deps_initialized = True
        logger.debug("[DEPS] _ensure_dependencies complete")

from photo_cleaner.config import AppConfig
from photo_cleaner.pipeline.scoring_constants import ScoringConstants  # BUG-M1 FIX

logger = logging.getLogger(__name__)


def _resolve_face_mesh_ctor():
    """Resolve MediaPipe Face Mesh constructor from available shims once."""
    global _FACE_MESH_CTOR, _FACE_MESH_IMPORT_ERROR, _FACE_MESH_RESOLVED, _mp

    if _FACE_MESH_RESOLVED:
        return _FACE_MESH_CTOR

    _FACE_MESH_RESOLVED = True
    if not MEDIAPIPE_AVAILABLE or _mp is None:
        _FACE_MESH_IMPORT_ERROR = "mediapipe not installed"
        return None

    try:
        if hasattr(_mp, "solutions"):
            _FACE_MESH_CTOR = _mp.solutions.face_mesh.FaceMesh
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
                if "mediapipe.python" in str(mnfe):
                    pass
                else:
                    raise
        # Fallback: MediaPipe Tasks FaceLandmarker (no solutions module)
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
                        pass

            _FACE_MESH_CTOR = _FaceMeshTasksWrapper
            return _FACE_MESH_CTOR
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            _FACE_MESH_IMPORT_ERROR = (
                "MediaPipe solutions not available and tasks fallback failed: " + str(e)
            )
            logger.debug(f"Face Mesh fallback failed: {e}", exc_info=True)
            return None
    except (ImportError, AttributeError, ValueError) as e:  # noqa: BLE001
        _FACE_MESH_IMPORT_ERROR = str(e)
        logger.debug(f"Face Mesh import error: {e}", exc_info=True)
        return None


_HAAR_CASCADE_DIR_CACHE: Path | None = None
_HAAR_CASCADE_DIR_CHECKED = False


def _resolve_haar_cascade_dir() -> Path | None:
    global _HAAR_CASCADE_DIR_CACHE, _HAAR_CASCADE_DIR_CHECKED
    if _HAAR_CASCADE_DIR_CHECKED:
        return _HAAR_CASCADE_DIR_CACHE

    _HAAR_CASCADE_DIR_CHECKED = True
    
    # Note: We don't check if _cv2 is loaded because the resolver should work
    # even before cv2 is lazily imported. We'll just check the filesystem paths.
    if not CV2_AVAILABLE:
        _HAAR_CASCADE_DIR_CACHE = None
        return _HAAR_CASCADE_DIR_CACHE

    candidates = []
    try:
        env_dir = os.environ.get("PHOTOCLEANER_HAAR_CASCADE_DIR") or os.environ.get("OPENCV_HAAR_CASCADE_DIR")
        if env_dir:
            candidates.append(Path(env_dir))
    except Exception:
        pass
    
    # Try to get cv2 module for path resolution (might not be lazily imported yet)
    cv2_module = _cv2
    if cv2_module is None:
        try:
            import cv2 as cv2_temp
            cv2_module = cv2_temp
        except Exception:
            cv2_module = None
    
    if cv2_module is not None:
        try:
            data_dir = getattr(cv2_module.data, "haarcascades", None)
            if data_dir:
                candidates.append(Path(data_dir))
        except Exception:
            pass
        try:
            module_dir = Path(cv2_module.__file__).resolve().parent
            candidates.append(module_dir / "data" / "haarcascades")
            candidates.append(module_dir / "data")  # Haar cascades are directly in data/, not data/haarcascades/
            candidates.append(module_dir.parent / "cv2" / "data" / "haarcascades")
            candidates.append(module_dir.parent / "cv2" / "data")
        except Exception:
            pass
    
    try:
        app_dir = AppConfig.get_app_dir()
        candidates.append(app_dir / "_internal" / "cv2" / "data" / "haarcascades")
        candidates.append(app_dir / "_internal" / "cv2" / "data")
        candidates.append(app_dir / "cv2" / "data" / "haarcascades")
        candidates.append(app_dir / "cv2" / "data")
    except Exception:
        pass
    try:
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        if meipass:
            candidates.append(meipass / "cv2" / "data" / "haarcascades")
            candidates.append(meipass / "cv2" / "data")
            candidates.append(meipass / "_internal" / "cv2" / "data" / "haarcascades")
            candidates.append(meipass / "_internal" / "cv2" / "data")
    except Exception:
        pass

    for candidate in candidates:
        path = candidate
        if not path.exists():
            continue
        if list(path.glob("haarcascade_*.xml")):  # Match haarcascade_ pattern directly
            _HAAR_CASCADE_DIR_CACHE = path
            logger.info("Haar cascades found at %s", path)
            return _HAAR_CASCADE_DIR_CACHE

    try:
        app_dir = AppConfig.get_app_dir()
        for root in (app_dir, app_dir / "_internal"):
            if not root.exists():
                continue
            match = next(root.rglob("haarcascade_frontalface_default.xml"), None)
            if match is not None:
                _HAAR_CASCADE_DIR_CACHE = match.parent
                logger.info("Haar cascades found at %s", match.parent)
                return _HAAR_CASCADE_DIR_CACHE
    except Exception:
        pass

    logger.warning("Haar cascade directory not found; face fallback disabled")
    _HAAR_CASCADE_DIR_CACHE = None
    return _HAAR_CASCADE_DIR_CACHE


class CameraProfile:
    """PHASE 3: Camera-specific calibration for fair scoring across devices.
    
    Different smartphones have different hardware characteristics that affect
    sharpness variance and resolution capabilities:
    - iPhone: Aggressive computational photography → higher sharpness variance
    - Samsung: Different sensor characteristics → different sharpness patterns
    - Pixel: Heavy noise reduction → different sharpness profile
    - OnePlus, etc.: Varied characteristics
    
    PHASE 4 TASK 4: Dynamic phone database with auto-registration.
    Automatically detects new camera models and initializes with standard factors.
    """
    
    # Sharpness divisor calibration (base 5.0 for 8MP photos)
    # Higher value = more aggressive normalization = fairer scoring
    PROFILE_SHARPNESS_FACTOR = {
        "iPhone": 1.0,      # Aggressive computational photography
        "Samsung": 1.2,     # Stronger sensors but different processing
        "Pixel": 1.3,       # Aggressive noise reduction
        "OnePlus": 1.1,     # Balanced processing
        "Xiaomi": 1.15,     # Similar to OnePlus
        "Huawei": 1.1,      # Balanced
        "Motorola": 1.05,   # Minimal processing
        "LG": 1.08,         # Minimal processing
        "unknown": 1.0,     # BUG-H2 FIX: Explicit handling for images without EXIF
        "default": 1.0,     # Fallback for any other camera
    }
    
    # Resolution scaling factor
    # Accounts for actual sensor capabilities across generations
    PROFILE_RESOLUTION_FACTOR = {
        "iPhone": {"iPhone-12": 12.0, "iPhone-13": 12.0, "iPhone-14": 12.0, "iPhone-15": 12.0, "default": 12.0},
        "Samsung": {"S20": 12.0, "S21": 12.0, "S22": 50.0, "S23": 50.0, "S24": 50.0, "default": 12.0},
        "Pixel": {"Pixel-4": 12.0, "Pixel-5": 12.0, "Pixel-6": 12.0, "Pixel-7": 12.0, "Pixel-8": 12.0, "default": 12.0},
        "default": 12.0,
    }
    
    # PHASE 4 TASK 4: Dynamic database registry (camera_model -> metadata)
    DYNAMIC_DATABASE = {
        # Structure: "camera_model" -> {"generation": "...", "first_seen": timestamp, "keep_rate": 0.0-1.0}
    }
    
    @staticmethod
    def extract_camera_model(exif_data: dict) -> str:
        """PHASE 3 TASK 1: Extract camera model from EXIF.
        PHASE 4 TASK 4: Register unknown models in dynamic database.
        
        Returns:
            Camera manufacturer (iPhone, Samsung, Pixel, etc.) or 'unknown'
        """
        if not exif_data:
            return "unknown"
        
        # Try common EXIF fields
        model = exif_data.get("Model", "").upper()
        make = exif_data.get("Make", "").upper()
        
        # Extract full model name for dynamic registration
        full_model_name = f"{make}_{model}".strip("_")
        
        # Identify by model/make
        if "IPHONE" in model or "IPHONE" in make:
            camera_model = "iPhone"
        elif "SAMSUNG" in model or "SAMSUNG" in make:
            camera_model = "Samsung"
        elif "PIXEL" in model or "PIXEL" in make:
            camera_model = "Pixel"
        elif "ONEPLUS" in model or "ONEPLUS" in make:
            camera_model = "OnePlus"
        elif "XIAOMI" in model or "XIAOMI" in make:
            camera_model = "Xiaomi"
        elif "HUAWEI" in model or "HUAWEI" in make:
            camera_model = "Huawei"
        elif "MOTOROLA" in model or "MOTOROLA" in make:
            camera_model = "Motorola"
        elif "LG" in model or "LG" in make:
            camera_model = "LG"
        else:
            camera_model = "unknown"
        
        # PHASE 4 TASK 4: Register new camera models in dynamic database
        if full_model_name and camera_model != "unknown":
            CameraProfile._register_dynamic_camera(full_model_name, camera_model)
        
        return camera_model
    
    @staticmethod
    def _register_dynamic_camera(full_model_name: str, camera_type: str) -> None:
        """PHASE 4 TASK 4: Register unknown camera model in dynamic database.
        
        Automatically detects new camera models and stores them with:
        - Camera type (iPhone, Samsung, etc.)
        - First seen timestamp
        - Initial keep_rate and statistics for ML
        
        Args:
            full_model_name: Full camera model string from EXIF (e.g., "Apple iPhone 15")
            camera_type: Classified type (iPhone, Samsung, Pixel, etc.)
        """
        import time
        
        # Only register if not already in dynamic database
        if full_model_name in CameraProfile.DYNAMIC_DATABASE:
            return
        
        # Register with standard initialization
        CameraProfile.DYNAMIC_DATABASE[full_model_name] = {
            "camera_type": camera_type,
            "generation": "auto-detected",  # Will be refined by ML
            "first_seen": int(time.time()),
            "keep_rate": 0.5,  # Start with neutral rate for statistics
            "sample_count": 0,
        }
        
        logger.info(
            f"[PHASE-4] Dynamic database: Registered new camera '{full_model_name}' "
            f"(type: {camera_type})"
        )
    
    @staticmethod
    def get_dynamic_cameras() -> dict:
        """PHASE 4 TASK 4: Get all dynamically registered cameras.
        
        Returns:
            Dictionary of newly registered camera models
        """
        return CameraProfile.DYNAMIC_DATABASE.copy()
    
    @staticmethod
    def get_sharpness_factor(camera_model: str) -> float:
        """PHASE 3 TASK 1: Get sharpness normalization factor for camera."""
        factor = CameraProfile.PROFILE_SHARPNESS_FACTOR.get(
            camera_model,
            CameraProfile.PROFILE_SHARPNESS_FACTOR["default"]
        )
        return factor
    
    @staticmethod
    def get_resolution_baseline(camera_model: str, model_name: str = None) -> float:
        """PHASE 3 TASK 1: Get resolution baseline for camera generation."""
        if camera_model not in CameraProfile.PROFILE_RESOLUTION_FACTOR:
            return CameraProfile.PROFILE_RESOLUTION_FACTOR["default"]
        
        profiles = CameraProfile.PROFILE_RESOLUTION_FACTOR[camera_model]
        if model_name and model_name in profiles:
            return profiles[model_name]
        
        return profiles.get("default", 12.0)


@dataclass
class PersonEyeStatus:
    """Status of eyes for a single detected person."""
    
    person_id: int  # Identifier for this person in the image
    eyes_open: bool  # Whether both eyes are detected as open
    face_confidence: float  # Detection confidence (0.0-1.0)
    face_size_pixels: int  # Area of detected face in pixels
    face_sharpness: float = 0.0  # Sharpness of face region
    eyes_open_score: Optional[float] = None  # Eye openness score (0-100)
    gaze_score: Optional[float] = None  # Eye contact score (0-100)
    head_pose_score: Optional[float] = None  # Head pose score (0-100)
    smile_score: Optional[float] = None  # Smile score (0-100)
    
    # BUG-H4 FIX: Add serialization methods for caching/multiprocessing support
    def to_dict(self) -> dict:
        """Serialize for caching/multiprocessing.
        
        Returns:
            Dictionary with all fields for JSON/pickle serialization
        """
        return {
            "person_id": self.person_id,
            "eyes_open": self.eyes_open,
            "face_confidence": self.face_confidence,
            "face_size_pixels": self.face_size_pixels,
            "face_sharpness": self.face_sharpness,
            "eyes_open_score": self.eyes_open_score,
            "gaze_score": self.gaze_score,
            "head_pose_score": self.head_pose_score,
            "smile_score": self.smile_score,
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'PersonEyeStatus':
        """Deserialize from cache.
        
        Args:
            data: Dictionary with serialized fields
            
        Returns:
            PersonEyeStatus instance
        """
        return PersonEyeStatus(
            person_id=data.get("person_id", 0),
            eyes_open=data.get("eyes_open", False),
            face_confidence=data.get("face_confidence", 0.0),
            face_size_pixels=data.get("face_size_pixels", 0),
            face_sharpness=data.get("face_sharpness", 0.0),
            eyes_open_score=data.get("eyes_open_score"),
            gaze_score=data.get("gaze_score"),
            head_pose_score=data.get("head_pose_score"),
            smile_score=data.get("smile_score"),
        )


@dataclass
class FaceQuality:
    """Face quality metrics from MediaPipe Face Mesh.
    
    Updated to support multiple people per image:
    - has_face: True if any face detected
    - all_eyes_open: True only if ALL detected people have eyes open
    - person_eye_statuses: List of eye status for each person
    - num_faces: Total number of faces detected
    """
    
    has_face: bool
    eyes_open: bool = False  # DEPRECATED: Use all_eyes_open for correctness
    gaze_forward: bool = False
    head_straight: bool = False
    face_sharpness: float = 0.0  # Main person's sharpness
    confidence: float = 0.0  # Main person's confidence
    num_faces: int = 0
    eye_count: int = 0  # Detected eyes in main face
    face_count: int = 0  # For backward compatibility
    
    # NEW: Multi-person support
    all_eyes_open: bool = False  # True only if ALL people have eyes open
    person_eye_statuses: list = None  # List of PersonEyeStatus objects
    
    # NEW: Best-person metrics (for multi-face selection)
    best_person_id: int = 0
    eye_open_score: Optional[float] = None
    gaze_forward_score: Optional[float] = None
    head_pose_score: Optional[float] = None
    smile_score: Optional[float] = None
    
    def __post_init__(self):
        """Initialize person_eye_statuses if not provided."""
        if self.person_eye_statuses is None:
            self.person_eye_statuses = []


@dataclass
class QualityResult:
    """Complete quality analysis result."""
    
    path: Path
    face_quality: Optional[FaceQuality] = None
    overall_sharpness: float = 0.0
    lighting_score: float = 0.0
    resolution_score: float = 0.0
    width: int = 0
    height: int = 0
    total_score: float = 0.0
    error: Optional[str] = None
    
    # PHASE 3: Camera profile tracking
    camera_model: str = "unknown"  # iPhone, Samsung, Pixel, etc.
    exif_data: Optional[dict] = None  # Raw EXIF metadata for camera detection
    
    # PHASE 4 TASK 2: Sensor metadata for advanced scoring
    iso_value: Optional[int] = None  # ISO sensitivity (100-3200+)
    aperture_value: Optional[float] = None  # f-number (f/1.4, f/2.8, etc.)
    focal_length: Optional[float] = None  # Focal length in mm
    exposure_time: Optional[float] = None  # Shutter speed in seconds


class QualityAnalyzer:
    """
    Quality analyzer using MediaPipe Face Mesh.
    
    Only runs on images within duplicate groups to minimize cost.
    """
    
    def __init__(
        self,
        use_face_mesh: bool = True,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        """
        Initialize quality analyzer.
        
        Args:
            use_face_mesh: Enable MediaPipe Face Mesh analysis
            min_detection_confidence: Face detection confidence threshold
            min_tracking_confidence: Face tracking confidence threshold
        """
        logger.info("[INIT] QualityAnalyzer.__init__ started")
        # CRITICAL: Lazy load all numpy-dependent modules
        logger.debug("[INIT] Calling _ensure_dependencies()...")
        _ensure_dependencies()
        logger.debug("[INIT] _ensure_dependencies() returned")
        
        # Feature flags (progressive eye detection)
        # Env: PHOTOCLEANER_EYE_DETECTION_STAGE: 1 (Haar), 2 (dlib), 3 (MediaPipe)
        # Default: 1
        logger.debug("[INIT] Reading EYE_DETECTION_STAGE...")
        try:
            requested_stage = int(os.environ.get("PHOTOCLEANER_EYE_DETECTION_STAGE", "1"))
        except (ValueError, TypeError):
            logger.debug("Invalid EYE_DETECTION_STAGE value, using default", exc_info=True)
            requested_stage = 1
        
        # GRACEFUL FALLBACK: Auto-adjust stage based on available dependencies
        logger.debug(f"[INIT] Determining available stage (requested={requested_stage})...")
        self._eye_detection_stage = self._determine_available_stage(requested_stage)
        logger.debug(f"[INIT] Eye detection stage set to {self._eye_detection_stage}")
        
        # Log if fallback occurred
        if self._eye_detection_stage != requested_stage:
            logger.info(
                f"Eye Detection: Stufe {requested_stage} angefordert, aber nur Stufe {self._eye_detection_stage} "
                f"verfügbar (fehlende Dependencies). Fallback aktiviert."
            )
        else:
            logger.debug(f"Eye Detection: Stufe {self._eye_detection_stage} aktiviert")

        logger.debug(f"[INIT] Setting use_face_mesh={use_face_mesh and MEDIAPIPE_AVAILABLE}")
        self.use_face_mesh = use_face_mesh and MEDIAPIPE_AVAILABLE
        self._face_mesh_warning_logged = False
        self.face_mesh = None
        self._base_options = None
        
        # Cache Haar Cascades (loaded once, reused for all images) - PERFORMANCE
        logger.debug("[INIT] Loading Haar Cascades...")
        self.face_cascade = None
        self.eye_cascade = None
        if CV2_AVAILABLE:
            try:
                cascade_dir = _resolve_haar_cascade_dir()
                if cascade_dir is not None:
                    face_path = cascade_dir / "haarcascade_frontalface_default.xml"
                    eye_path = cascade_dir / "haarcascade_eye_tree_eyeglasses.xml"
                    self.face_cascade = _cv2.CascadeClassifier(str(face_path))
                    self.eye_cascade = _cv2.CascadeClassifier(str(eye_path))
                    if self.face_cascade.empty() or self.eye_cascade.empty():
                        logger.warning("Failed to load Haar cascades from %s", cascade_dir)
                        self.face_cascade = None
                        self.eye_cascade = None
            except (OSError, IOError, RuntimeError) as e:
                logger.warning(f"Failed to load Haar Cascades: {e}", exc_info=True)
        logger.debug("[INIT] Haar Cascades loaded")
        
        # PHASE 2026: Cache MTCNN detector (singleton instance)
        # Load detector ONCE and reuse across all images → significant speedup
        # P0 FIX: Add threading.Lock to prevent race condition with multiple threads
        logger.debug("[INIT] Initializing MTCNN cache...")
        self._mtcnn_detector_cache = None  # Lazy-loaded on first use
        self._mtcnn_lock = threading.Lock()  # P0 FIX: Thread-safe detector initialization
        self._mtcnn_infer_lock = threading.Lock()
        logger.debug("[INIT] MTCNN locks created")
        if MTCNN_AVAILABLE:
            logger.info("MTCNN: Available and ready (using TensorFlow backend)")
        elif _MTCNN_IMPORT_ERROR:
            if "Disabled via PHOTOCLEANER_FACE_DETECTOR" in _MTCNN_IMPORT_ERROR or "Skipped by PHOTOCLEANER_SKIP_HEAVY_DEPS" in _MTCNN_IMPORT_ERROR:
                logger.info(f"MTCNN: {_MTCNN_IMPORT_ERROR}")
            else:
                logger.warning(f"MTCNN: Import failed - {_MTCNN_IMPORT_ERROR}")
        else:
            logger.warning("MTCNN: Not available (unknown reason)")
        
        logger.debug("[INIT] Checking MediaPipe/CV2 availability...")
        if not MEDIAPIPE_AVAILABLE:
            # Only warn if MediaPipe was requested but failed to import
            if use_face_mesh and _MEDIAPIPE_IMPORT_ERROR:
                logger.warning(f"MediaPipe import failed but was requested for face mesh analysis: {_MEDIAPIPE_IMPORT_ERROR}")
                logger.warning("⚠ Face Mesh analysis will be disabled, using fallback quality scoring")
            self.use_face_mesh = False

        if not CV2_AVAILABLE:
            if use_face_mesh:
                logger.warning("OpenCV not available but was requested - Face Mesh analysis disabled")
            self.use_face_mesh = False
        else:
            # Store thresholds even if we instantiate FaceMesh on-demand later
            logger.debug("[INIT] Storing face mesh thresholds...")
            self._min_detection_confidence = min_detection_confidence
            self._min_tracking_confidence = min_tracking_confidence

            # FEATURE: MediaPipe Model Caching (singleton instance)
            # Load model ONCE and reuse across all images → 10-100x speedup
            self._face_mesh_cache = None  # Lazy-loaded on first use
            logger.debug("MediaPipe Face Mesh: Caching enabled (load-on-first-use)")

            # PHASE 2 FIX: Config change detection for cache invalidation
            logger.debug("[INIT] Initializing config hash...")
            self._last_config_hash = None  # Track config changes
            try:
                self._init_config_hash()  # Initialize hash on startup
                logger.debug("[INIT] Config hash initialized")
            except Exception as e:
                logger.error(f"[INIT] CRITICAL: _init_config_hash() failed: {e}", exc_info=True)
                raise

            # BUG-C5 FIX: Thread lock for cache invalidation to prevent race conditions
            logger.debug("[INIT] Creating cache lock...")
            self._cache_lock = threading.Lock()
            logger.debug("[INIT] Cache lock created")
        
        logger.info("[INIT] QualityAnalyzer.__init__ complete")

    def warmup(self) -> None:
        """Preload heavy models to avoid first-image delay."""
        global MTCNN_AVAILABLE, _MTCNN_IMPORT_ERROR, _MTCNN_WARNING_LOGGED
        
        logger.debug("[WARMUP] Starting model warmup...")
        
        try:
            if self.use_face_mesh:
                logger.debug("[WARMUP] Loading Face Mesh model...")
                _ = self._get_face_mesh_model()
                logger.debug("[WARMUP] Face Mesh model loaded successfully")
        except (ImportError, RuntimeError, AttributeError) as e:
            logger.warning("Face Mesh warmup failed: %s", e, exc_info=True)

        try:
            if MTCNN_AVAILABLE and self._mtcnn_detector_cache is None:
                logger.info("[WARMUP] MTCNN: Preloading detector (this may take 10-30 seconds)...")
                import time
                start = time.time()
                self._mtcnn_detector_cache = MTCNN()
                elapsed = time.time() - start
                logger.info(f"[WARMUP] MTCNN detector loaded in {elapsed:.1f}s")
            elif MTCNN_AVAILABLE:
                logger.debug("[WARMUP] MTCNN already loaded")
            else:
                logger.debug("[WARMUP] MTCNN not available, skipping")
        except (ImportError, RuntimeError, AttributeError, OSError, Exception) as e:
            # Catch all exceptions including TensorFlow DLL errors
            MTCNN_AVAILABLE = False
            _MTCNN_IMPORT_ERROR = f"Warmup failed: {e}"
            _MTCNN_WARNING_LOGGED = True  # Mark as already logged
            logger.warning(f"[WARMUP] MTCNN warmup failed ({type(e).__name__}): {e}. Falling back to Haar Cascade for all images.")
        
        logger.debug("[WARMUP] Warmup complete")

    def _determine_available_stage(self, requested_stage: int) -> int:
        """
        Determine the highest available eye detection stage based on installed dependencies.
        
        Graceful fallback logic:
        - Stage 3: Requires MediaPipe + OpenCV
        - Stage 2: Requires dlib + OpenCV
        - Stage 1: Requires OpenCV (Haar Cascades)
        
        Args:
            requested_stage: The stage requested by user (1, 2, or 3)
        
        Returns:
            The highest available stage <= requested_stage
        """
        # Clamp to valid range
        requested_stage = max(1, min(3, requested_stage))
        
        # Check Stage 3: MediaPipe
        if requested_stage >= 3:
            if MEDIAPIPE_AVAILABLE and CV2_AVAILABLE:
                return 3
            else:
                if not MEDIAPIPE_AVAILABLE:
                    logger.debug("MediaPipe nicht verfügbar, falle zurück auf Stufe 2")
                # Fall through to check Stage 2
        
        # Check Stage 2: dlib
        if requested_stage >= 2:
            if DLIB_AVAILABLE and CV2_AVAILABLE:
                return 2
            else:
                if not DLIB_AVAILABLE:
                    logger.debug("dlib nicht verfügbar, falle zurück auf Stufe 1")
                # Fall through to Stage 1
        
        # Stage 1: Haar Cascades (always available with OpenCV)
        if CV2_AVAILABLE:
            return 1
        
        # Fallback: No OpenCV available, disable eye detection
        logger.warning("OpenCV nicht verfügbar, Augenerkennung deaktiviert")
        return 0  # Will be handled in _analyze_faces_progressive
    
    def get_actual_stage(self) -> int:
        """
        Get the actual eye detection stage being used (after fallback).
        
        Useful for UI to show current capabilities.
        """
        return self._eye_detection_stage
    
    def get_stage_info(self) -> dict:
        """
        Get detailed info about current stage and available stages.
        
        Returns:
            Dict with keys:
            - current_stage: Active stage (0-3)
            - available_stages: List of usable stages
            - missing_for_stage_2: List of missing deps for Stage 2
            - missing_for_stage_3: List of missing deps for Stage 3
        """
        available_stages = []
        if CV2_AVAILABLE:
            available_stages.append(1)
        if DLIB_AVAILABLE and CV2_AVAILABLE:
            available_stages.append(2)
        if MEDIAPIPE_AVAILABLE and CV2_AVAILABLE:
            available_stages.append(3)
        
        missing_stage_2 = []
        if not CV2_AVAILABLE:
            missing_stage_2.append("opencv-python")
        if not DLIB_AVAILABLE:
            missing_stage_2.append("dlib")
        
        missing_stage_3 = []
        if not CV2_AVAILABLE:
            missing_stage_3.append("opencv-python")
        if not MEDIAPIPE_AVAILABLE:
            missing_stage_3.append("mediapipe")
        
        # PHASE 2026: Include MTCNN availability info
        face_detector = os.environ.get("PHOTOCLEANER_FACE_DETECTOR", "mtcnn").lower()
        
        return {
            "current_stage": self._eye_detection_stage,
            "available_stages": available_stages,
            "missing_for_stage_2": missing_stage_2,
            "missing_for_stage_3": missing_stage_3,
            "mtcnn_available": MTCNN_AVAILABLE,
            "face_detector": face_detector,
            "face_detector_active": "mtcnn" if (face_detector == "mtcnn" and MTCNN_AVAILABLE) else "haar"
        }
    
    def _init_config_hash(self) -> None:
        """PHASE 2 FIX: Initialize hash of current config for change detection."""
        import hashlib
        quality_threshold = getattr(AppConfig, "QUALITY_THRESHOLD", "NA")
        config_state = f"{quality_threshold}_{AppConfig.is_debug()}"
        self._last_config_hash = hashlib.md5(config_state.encode()).hexdigest()
    
    def _check_config_changed(self) -> bool:
        """PHASE 2 FIX: Check if configuration has changed since last call.
        
        Returns:
            True if config changed, triggers cache invalidation
        """
        import hashlib
        quality_threshold = getattr(AppConfig, "QUALITY_THRESHOLD", "NA")
        config_state = f"{quality_threshold}_{AppConfig.is_debug()}"
        current_hash = hashlib.md5(config_state.encode()).hexdigest()
        
        if current_hash != self._last_config_hash:
            logger.info("[PHASE-2] Config changed detected - invalidating cache")
            self._last_config_hash = current_hash
            return True
        return False
    
    def _invalidate_face_mesh_cache(self) -> None:
        """P1 FIX #6: Invalidate Face Mesh cache on config change with proper error handling.
        
        BUG-C5 FIX: Thread-safe invalidation to prevent race conditions in multiprocessing.
        Prevents stale model using old configuration.
        
        P1 FIX #6: Improved error handling - don't silently ignore close() errors.
        """
        # BUG-C5 FIX: Use lock to prevent race condition when multiple processes invalidate simultaneously
        with self._cache_lock:
            if not self._face_mesh_cache:
                return
            
            try:
                logger.debug("Closing Face Mesh cache due to config change...")
                self._face_mesh_cache.close()
                self._face_mesh_cache = None
                logger.info("Face Mesh cache invalidated successfully")
            except (RuntimeError, AttributeError) as e:
                # P1 FIX #6: Don't silently fail - log what happened
                logger.error(
                    f"Failed to close Face Mesh cache properly ({type(e).__name__}): {e}. "
                    f"Cache is being cleared anyway, but analyzer may need restart if errors persist.",
                    exc_info=True
                )
                # Clear reference anyway, but model may be partially initialized
                self._face_mesh_cache = None
            except Exception as e:
                # Unexpected error type
                logger.critical(
                    f"Unexpected error while invalidating Face Mesh cache: {type(e).__name__}: {e}. "
                    f"Analyzer state may be corrupted.",
                    exc_info=True
                )
                self._face_mesh_cache = None
    
    def _get_face_mesh_model(self):
        """FEATURE: Get cached MediaPipe Face Mesh model (singleton pattern).
        
        PHASE 2: Includes config-change invalidation hook.
        Loads model on first use, then reuses same instance for all images.
        This gives 10-100x speedup vs creating new instance per image.
        
        Returns:
            mp.solutions.face_mesh.FaceMesh instance or None
        """
        # Check for config changes and invalidate cache if needed
        if self._check_config_changed():
            self._invalidate_face_mesh_cache()
        if not MEDIAPIPE_AVAILABLE or not self.use_face_mesh:
            return None
        
        # Lazy-load on first use
        if self._face_mesh_cache is None:
            try:
                face_mesh_ctor = _resolve_face_mesh_ctor()
                if face_mesh_ctor is None:
                    global _FACE_MESH_WARNED  # noqa: PLW0603
                    if not _FACE_MESH_WARNED and _FACE_MESH_IMPORT_ERROR:
                        logger.warning(
                            "Failed to import MediaPipe solutions API (Face Mesh disabled): %s",
                            _FACE_MESH_IMPORT_ERROR,
                        )
                        _FACE_MESH_WARNED = True
                    self.use_face_mesh = False
                    return None

                self._face_mesh_cache = face_mesh_ctor(
                    static_image_mode=True,
                    max_num_faces=10,  # Erhöht für Gruppenbilder, aber mit strengerer Confidence
                    refine_landmarks=True,
                    min_detection_confidence=0.7,  # Erhöht von 0.5 auf 0.7 um False Positives zu reduzieren
                    min_tracking_confidence=self._min_tracking_confidence,
                )
                logger.debug("MediaPipe Face Mesh model loaded and cached (min_detection_confidence=0.7)")
            except (ImportError, RuntimeError, AttributeError, ValueError) as e:
                logger.warning(f"Failed to load MediaPipe Face Mesh: {e}", exc_info=True)
                self.use_face_mesh = False
                return None
        
        return self._face_mesh_cache
    
    def __del__(self) -> None:
        """P0 FIX: Cleanup resources on destruction to prevent memory leaks.
        
        MediaPipe models hold large TensorFlow session state in memory (~50-100MB).
        Without cleanup, batch processing accumulates memory leaks.
        """
        self._cleanup_models()

    def _cleanup_models(self) -> None:
        """P0 FIX: Close all model resources to free memory."""
        # Clean up MediaPipe Face Mesh cache
        if hasattr(self, '_face_mesh_cache') and self._face_mesh_cache:
            try:
                if hasattr(self._face_mesh_cache, 'close'):
                    self._face_mesh_cache.close()
                self._face_mesh_cache = None
                logger.debug("MediaPipe Face Mesh cache cleaned up in _cleanup_models")
            except Exception as e:
                logger.debug(f"Error closing face mesh: {e}")
        
        # Clean up MTCNN detector cache
        if hasattr(self, '_mtcnn_detector_cache') and self._mtcnn_detector_cache:
            try:
                # MTCNN doesn't have close(), but we can clear the TensorFlow session reference
                # This allows the TensorFlow session to be garbage collected
                self._mtcnn_detector_cache = None
                logger.debug("MTCNN detector cache cleaned up in _cleanup_models")
            except Exception as e:
                logger.debug(f"Error cleaning MTCNN: {e}")
        
        # Clean up legacy face_mesh attribute
        if hasattr(self, 'face_mesh') and self.face_mesh:
            try:
                if hasattr(self.face_mesh, 'close'):
                    self.face_mesh.close()
                self.face_mesh = None
                logger.debug("Legacy face_mesh cleaned up in _cleanup_models")
            except Exception as e:
                logger.debug(f"Error closing legacy face_mesh: {e}")
    
    def _get_exif_orientation_from_pil(self, pil_image, image_path: Path) -> int:
        """
        OPTIMIZATION: Get EXIF orientation from already-opened PIL image if available.
        Returns 1 (no rotation) if not found.
        
        Avoids redundant PIL.Image.open() calls when PIL image is already loaded.
        """
        try:
            from PIL.ExifTags import TAGS
            if pil_image is None:
                pil_image = Image.open(image_path)
            exif_data = pil_image.getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    if tag_name == "Orientation":
                        return value
        except (OSError, IOError, AttributeError):
            logger.debug("Could not extract EXIF orientation", exc_info=True)
            pass
        return 1
    
    def _extract_exif_data_from_pil(self, pil_image, image_path: Path) -> dict:
        """OPTIMIZATION: Extract EXIF data from already-opened PIL image if available.
        P2 FIX #14: Validate EXIF data size to prevent DoS attacks.
        PHASE 3 TASK 1: Extract EXIF data for camera model detection.
        PHASE 4 TASK 2: Extended to include sensor metadata (ISO, Aperture, Focal Length, Exposure).
        
        Avoids redundant PIL.Image.open() calls when PIL image is already loaded.
        
        P2 FIX #14: DoS Protection:
        - Limit EXIF field count (prevent malicious JPEGs with thousands of tags)
        - Limit JSON size (prevent database bloat)
        - Truncate to essential fields if limits exceeded
        
        Returns:
            Dictionary with EXIF fields including camera model and sensor metadata or empty dict if not available
        """
        # P2 FIX #14: DoS Prevention Constants
        MAX_EXIF_FIELDS = 500  # Don't accept more than 500 EXIF tags
        MAX_EXIF_JSON_SIZE = 100 * 1024  # 100KB max for serialized EXIF
        
        try:
            from PIL.ExifTags import TAGS
            if pil_image is None:
                pil_image = Image.open(image_path)
            
            exif_raw = pil_image.getexif()
            
            if not exif_raw:
                return {}
            
            # P2 FIX #14: Check EXIF field count (DoS prevention)
            if len(exif_raw) > MAX_EXIF_FIELDS:
                logger.warning(
                    f"EXIF too many fields ({len(exif_raw)}) for {image_path.name}, "
                    f"truncating to {MAX_EXIF_FIELDS}"
                )
                # Keep only first N fields (arbitrary but limits damage)
                exif_raw = dict(list(exif_raw.items())[:MAX_EXIF_FIELDS])
            
            exif_dict = {}
            
            # Standard EXIF tag names for sensor metadata
            SENSOR_TAGS = {
                "ISOSpeedRatings": "iso_value",
                "PhotographicSensitivity": "iso_value",
                "ApertureValue": "aperture_value",
                "FNumber": "f_number",
                "FocalLength": "focal_length",
                "ExposureTime": "exposure_time",
                "ShutterSpeedValue": "shutter_speed_value",
            }
            
            # Camera identification tags
            CAMERA_TAGS = ("Model", "Make", "DateTime", "DateTimeOriginal")
            
            for tag_id, value in exif_raw.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                
                # Extract camera identification
                if tag_name in CAMERA_TAGS:
                    exif_dict[tag_name] = str(value)
                
                # Extract sensor metadata (PHASE 4 TASK 2)
                elif tag_name in SENSOR_TAGS:
                    sensor_key = SENSOR_TAGS[tag_name]
                    
                    # Parse numeric values with error handling
                    try:
                        if tag_name == "ISOSpeedRatings" or tag_name == "PhotographicSensitivity":
                            # BUG-C6 FIX: Validate ISO value is positive and within realistic range
                            iso_val = int(value) if isinstance(value, (int, float)) else int(str(value))
                            if 0 < iso_val <= 409600:  # Realistic range: 1 - 409600 (high-end cameras)
                                exif_dict["iso_value"] = iso_val
                            else:
                                logger.debug(f"ISO value {iso_val} out of realistic range for {image_path.name}")
                        
                        elif tag_name in ("ApertureValue", "FNumber"):
                            # BUG-C6 FIX: Prevent division by zero and validate aperture range
                            if isinstance(value, tuple) and len(value) == 2:
                                # Rational: (numerator, denominator)
                                if value[1] != 0:  # Prevent division by zero
                                    aperture_val = float(value[0]) / float(value[1])
                                else:
                                    logger.debug(f"Invalid aperture denominator 0 for {image_path.name}")
                                    continue
                            elif isinstance(value, (int, float)):
                                aperture_val = float(value)
                            else:
                                aperture_val = float(str(value))
                            
                            # Validate realistic aperture range: f/0.95 to f/64
                            if 0.5 < aperture_val < 100:
                                exif_dict["aperture_value"] = round(aperture_val, 2)
                            else:
                                logger.debug(f"Aperture value {aperture_val} out of realistic range for {image_path.name}")
                        
                        elif tag_name == "FocalLength":
                            # BUG-C6 FIX: Prevent division by zero and validate focal length range
                            if isinstance(value, tuple) and len(value) == 2:
                                if value[1] != 0:  # Prevent division by zero
                                    focal_val = float(value[0]) / float(value[1])
                                else:
                                    logger.debug(f"Invalid focal length denominator 0 for {image_path.name}")
                                    continue
                            else:
                                focal_val = float(value)
                            
                            # Validate realistic focal length range: 1mm to 3000mm
                            if 0 < focal_val < 5000:
                                exif_dict["focal_length"] = round(focal_val, 2)
                            else:
                                logger.debug(f"Focal length {focal_val} out of realistic range for {image_path.name}")
                        
                        elif tag_name == "ExposureTime":
                            # BUG-C6 FIX: Prevent division by zero and validate exposure time range
                            if isinstance(value, tuple) and len(value) == 2:
                                if value[1] != 0:  # Prevent division by zero
                                    exposure_val = float(value[0]) / float(value[1])
                                else:
                                    logger.debug(f"Invalid exposure time denominator 0 for {image_path.name}")
                                    continue
                            else:
                                exposure_val = float(value)
                            
                            # Validate realistic exposure range: 1/8000s to 30s
                            if 0.0001 < exposure_val < 60:
                                exif_dict["exposure_time"] = exposure_val
                            else:
                                logger.debug(f"Exposure time {exposure_val} out of realistic range for {image_path.name}")
                        
                        elif tag_name == "ShutterSpeedValue":
                            # BUG-C6 FIX: Prevent division by zero for shutter speed
                            if isinstance(value, tuple) and len(value) == 2:
                                if value[1] != 0:
                                    shutter_val = float(value[0]) / float(value[1])
                                    exif_dict["shutter_speed_value"] = shutter_val
                            else:
                                exif_dict["shutter_speed_value"] = float(value)
                    
                    except (ValueError, ZeroDivisionError, TypeError) as parse_err:
                        logger.debug(f"Failed to parse {tag_name}={value} for {image_path.name}: {parse_err}")
            
            # P2 FIX #14: Check serialized JSON size (DoS prevention)
            import json
            try:
                exif_json = json.dumps(exif_dict, default=str)
                exif_size = len(exif_json.encode('utf-8'))
                
                if exif_size > MAX_EXIF_JSON_SIZE:
                    logger.warning(
                        f"EXIF JSON too large ({exif_size} bytes) for {image_path.name}, "
                        f"keeping only essential fields"
                    )
                    # Keep only essential camera identification fields
                    essential_keys = {"Model", "Make", "DateTime", "DateTimeOriginal"}
                    exif_dict = {k: v for k, v in exif_dict.items() if k in essential_keys}
            except Exception as e:
                logger.debug(f"Failed to check EXIF JSON size: {e}")
            
            if not exif_dict:
                logger.debug(f"No EXIF metadata found for {image_path.name}")
            
            return exif_dict
        except (OSError, IOError, AttributeError) as e:
            logger.debug(f"EXIF extraction failed for {image_path.name}: {e}", exc_info=True)
            return {}
    
    def _extract_exif_data(self, image_path: Path) -> dict:
        """PHASE 3 TASK 1: Extract EXIF data for camera model detection.
        PHASE 4 TASK 2: Extended to include sensor metadata (ISO, Aperture, Focal Length, Exposure).
        
        DEPRECATED: Now delegates to _extract_exif_data_from_pil() for consistency.
        
        Returns:
            Dictionary with EXIF fields including camera model and sensor metadata or empty dict if not available
        """
        try:
            pil_image = Image.open(image_path)
            return self._extract_exif_data_from_pil(pil_image, image_path)
        except (OSError, IOError, AttributeError) as e:
            logger.debug(f"EXIF extraction failed for {image_path.name}: {e}", exc_info=True)
            return {}
    
    def _rotate_image_from_exif(self, img: NDArray, orientation: int) -> NDArray:
        """
        Rotate image based on EXIF orientation value (1-8).
        This fixes the issue where smartphone images are rotated in EXIF
        but OpenCV loads them unrotated, causing eye detection to fail.
        """
        if orientation == 1:
            return img  # No rotation
        elif orientation == 2:
            return cv2.flip(img, 1)  # Flip horizontal
        elif orientation == 3:
            return cv2.rotate(img, cv2.ROTATE_180)  # Rotate 180°
        elif orientation == 4:
            return cv2.flip(img, 0)  # Flip vertical
        elif orientation == 5:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif orientation == 6:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif orientation == 7:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif orientation == 8:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return img
    
    def _calculate_base_score(
        self,
        overall_sharpness: float,
        local_sharpness: float,
        detail_score: float,
        fg_bg_score: float,
        lighting_score: float,
        resolution_score: float,
        face_quality: FaceQuality,
        width: int,
        height: int
    ) -> float:
        """
        Phase 3 Enhancement: Calculate base quality score with or without faces.
        
        This method enables scoring for:
        - Portraits: Face quality (eyes open) is primary factor
        - Landscapes: Sharpness, lighting, and composition dominate
        - Architecture/Objects: Technical quality matters most
        
        Scoring Strategy:
        - WITH faces: Face quality (60%) + Technical (40%)
        - WITHOUT faces: Technical quality (100%) - Landscape Mode
        
        Technical Quality = Sharpness (30%) + Local Sharpness (20%) + Detail (15%) + Foreground/Background (10%) + Lighting (15%) + Resolution (10%)
        
        Args:
            overall_sharpness: Sharpness score (FFT 0-100 or legacy Laplacian variance)
            local_sharpness: Local sharpness consistency score (0-100)
            detail_score: Texture/detail score (0-100)
            fg_bg_score: Foreground/background separation score (0-100)
            lighting_score: Histogram-based score (0-100)
            resolution_score: Megapixel-based score (0-100)
            face_quality: Face analysis result (may be None)
            width: Image width in pixels
            height: Image height in pixels
        
        Returns:
            Combined quality score (0-100)
        """
        # Normalize sharpness to 0-100 scale
        # FFT-based sharpness already returns 0-100.
        # If a legacy Laplacian variance is passed, scale it.
        if overall_sharpness <= 100:
            sharpness_normalized = max(0.0, min(100.0, overall_sharpness))
        else:
            # Typical good images: 150-400, excellent: 300+
            # Blurry images: < 100
            sharpness_normalized = min(100, (overall_sharpness / 400) * 100)
        
        # Technical quality score (weighted average)
        technical_score = (
            sharpness_normalized * 0.30 +  # Global sharpness
            local_sharpness * 0.20 +       # Local sharpness consistency
            detail_score * 0.15 +          # Texture/detail richness
            fg_bg_score * 0.10 +           # Foreground/background separation
            lighting_score * 0.15 +        # Good exposure matters
            resolution_score * 0.10        # Resolution is bonus
        )

        # Motion blur & autofocus penalties (Week 5)
        motion_blur_penalty = self._calculate_motion_blur_penalty(
            sharpness_normalized, local_sharpness
        )
        autofocus_penalty = self._calculate_autofocus_penalty(
            sharpness_normalized, local_sharpness
        )
        technical_score = max(0.0, technical_score - motion_blur_penalty - autofocus_penalty)
        
        # Mode detection: Portrait vs Landscape
        has_faces = face_quality and face_quality.has_face
        
        if has_faces:
            # Portrait Mode: Face quality dominates
            face_score = self._calculate_face_quality_score(face_quality)
            
            # Weighted combination: 60% faces, 40% technical
            final_score = face_score * 0.60 + technical_score * 0.40
            
            logger.debug(
                f"Portrait Mode: Face={face_score:.1f} (60%), "
                f"Technical={technical_score:.1f} (40%) → {final_score:.1f}"
            )
        else:
            # Landscape Mode: Pure technical quality
            # No penalty for missing faces - landscapes are valid!
            final_score = technical_score
            
            logger.debug(
                f"Landscape Mode: Technical={technical_score:.1f} "
                f"(Sharp={sharpness_normalized:.1f}, Local={local_sharpness:.1f}, "
                f"Detail={detail_score:.1f}, FG/BG={fg_bg_score:.1f}, "
                f"Light={lighting_score:.1f}, Res={resolution_score:.1f}, "
                f"BlurPenalty={motion_blur_penalty:.1f}, AFPenalty={autofocus_penalty:.1f})"
            )
        
        return round(final_score, 2)
    
    def analyze_image(self, image_path: Path) -> QualityResult:
        """
        Analyze single image for quality metrics.
        
        Args:
            image_path: Path to image file
            
        Returns:
            QualityResult with all metrics
        """
        # Ensure dependencies are loaded (lazy import pattern)
        _ensure_dependencies()
        
        try:
            if not CV2_AVAILABLE:
                return QualityResult(
                    path=image_path,
                    error="OpenCV not available",
                )
            
            # Load image - try PIL first for HEIC support
            img = None
            pil_img = None
            original_width = None
            original_height = None
            pil_downsampled = False

            max_analysis_dimension = 2000
            downsample_enabled = True

            # Disable downsampling for MTCNN (it needs higher resolution)
            if MTCNN_AVAILABLE and self._mtcnn_detector_cache is not None:
                downsample_enabled = False
                logger.debug("  [PERF] Downsampling disabled (MTCNN requires higher resolution)")
            try:
                # Use OpenCV directly for common formats
                img = _cv2.imread(str(image_path))
                if img is not None:
                    original_height, original_width = img.shape[:2]
            except Exception:
                pass
            
            # Fallback to PIL for HEIC and other formats
            if img is None and _Image is not None:
                try:
                    pil_img = _Image.open(image_path)
                    original_width, original_height = pil_img.size

                    if downsample_enabled and (
                        original_width > max_analysis_dimension
                        or original_height > max_analysis_dimension
                    ):
                        target_size = (max_analysis_dimension, max_analysis_dimension)
                        try:
                            pil_img.draft("RGB", target_size)
                        except Exception:
                            pass

                        resample = _Image.Resampling.LANCZOS if hasattr(_Image, "Resampling") else _Image.LANCZOS
                        pil_img.thumbnail(target_size, resample)
                        pil_downsampled = True
                        logger.debug(
                            f"  [PERF] Downsampling (PIL) {original_width}x{original_height} "
                            f"-> {pil_img.size[0]}x{pil_img.size[1]} for quality analysis"
                        )

                    # Convert to RGB if needed
                    if pil_img.mode != "RGB":
                        pil_img = pil_img.convert("RGB")
                    # Convert PIL Image to OpenCV BGR format without cv2.cvtColor
                    rgb = np.asarray(pil_img)
                    img = rgb[:, :, ::-1].copy()
                except (OSError, IOError, AttributeError, ValueError) as e:
                    logger.debug(f"PIL fallback failed for {image_path}: {e}", exc_info=True)
            
            if img is None:
                return QualityResult(
                    path=image_path,
                    error="Failed to load image",
                )
            
            # OPTIMIZATION: Extract EXIF once from PIL image if available (avoid duplicate PIL.Image.open calls)
            # This eliminates the separate PIL opens that were happening in _get_exif_orientation and _extract_exif_data
            if pil_img is None and _Image is not None:
                try:
                    pil_img = _Image.open(image_path)
                except (OSError, IOError):
                    logger.debug(f"Could not open image with PIL for EXIF: {image_path}", exc_info=True)
                    pass
            
            # PHASE 2 WEEK 4 OPTIMIZATION: Resolution-Adaptive Processing
            # Large images (>2000px) are resized for quality analysis to improve performance
            # This provides 2-3x speedup on high-resolution images without quality loss
            # Quality metrics (sharpness, lighting, face detection) remain valid at lower resolution
            #
            # EXCEPTION: Skip downsampling if MTCNN is available and will be used
            # MTCNN requires sufficient resolution for multi-scale face detection
            # and handles its own internal scaling
            if original_width is None or original_height is None:
                original_height, original_width = img.shape[:2]

            if downsample_enabled and not pil_downsampled and (
                original_width > max_analysis_dimension or original_height > max_analysis_dimension
            ):
                # Calculate scale factor to fit within max_analysis_dimension
                scale_factor = min(
                    max_analysis_dimension / original_width,
                    max_analysis_dimension / original_height
                )
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                
                logger.debug(
                    f"  [PERF] Downsampling {original_width}x{original_height} → {new_width}x{new_height} "
                    f"(scale={scale_factor:.2f}) for quality analysis"
                )
                
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # CRITICAL FIX [BUG-C2]: Apply EXIF rotation IMMEDIATELY after image load
            # BEFORE any analysis (face detection, sharpness, etc.)
            # Many smartphone images are stored rotated in EXIF but OpenCV loads them unrotated.
            # Without this, eye detection fails on rotated images (false negatives on ~30% of phone portraits).
            # Severity: HIGH - Affects accuracy on ~30% of smartphone photos
            # Solution: Apply rotation before _analyze_faces_progressive() call below
            exif_orientation = self._get_exif_orientation_from_pil(pil_img, image_path)
            if exif_orientation != 1:
                logger.debug(f"  [BUG-C2 FIX] Applying EXIF rotation: {exif_orientation}")
                img = self._rotate_image_from_exif(img, exif_orientation)
            
            # PHASE 3 TASK 1: Extract EXIF for camera-aware scoring
            # OPTIMIZATION: Use cached PIL image to avoid redundant file I/O
            exif_data = self._extract_exif_data_from_pil(pil_img, image_path)
            camera_model = CameraProfile.extract_camera_model(exif_data)
            
            # PHASE 4 TASK 2: Extract sensor metadata for advanced scoring
            iso_value = exif_data.get("iso_value")
            aperture_value = exif_data.get("aperture_value")
            focal_length = exif_data.get("focal_length")
            exposure_time = exif_data.get("exposure_time")
            
            # IMPORTANT: Use ORIGINAL dimensions for resolution score, not downsampled
            # After downsampling, img.shape reflects the resized dimensions
            height, width = img.shape[:2]
            
            # Resolution score should reflect the actual image resolution (not analysis resolution)
            # Use original dimensions that were captured before downsampling
            resolution_score = (original_width * original_height) / 1_000_000  # Megapixels
            
            # DEBUG: Log image dimensions (show both original and analysis dimensions if different)
            orientation = "Portrait" if original_height > original_width else "Landscape"
            if width != original_width or height != original_height:
                logger.debug(
                    f"QualityAnalyzer: {image_path.name} → {orientation} "
                    f"{original_width}×{original_height} = {resolution_score:.1f}MP "
                    f"(analyzing at {width}×{height})"
                )
            else:
                logger.debug(
                    f"QualityAnalyzer: {image_path.name} → {orientation} "
                    f"{width}×{height} = {resolution_score:.1f}MP"
                )
            
            # Calculate overall sharpness (FFT-based, more robust than Laplacian)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            overall_sharpness = self._calculate_sharpness_fft(gray)
            local_sharpness = self._calculate_local_sharpness(gray)
            detail_score = self._calculate_detail_score(gray)
            fg_bg_score = self._calculate_foreground_background_score(gray)
            
            # Calculate lighting score (0-100 based on histogram)
            lighting_score = self._calculate_lighting_score(gray)
            # Week 3: Apply color cast penalty (green/magenta/blue tint)
            lighting_score = max(0.0, lighting_score - self._calculate_color_cast_penalty(img))
            
            # Progressive eye detection: Haar → dlib (optional) → MediaPipe (optional)
            try:
                face_quality = self._analyze_faces_progressive(img)
            except Exception as e:
                logger.exception(f"Face analysis failed for {image_path.name}")
                # Fallback: Return neutral score (no face detected)
                face_quality = FaceQuality(has_face=False)
            
            # Phase 3 Enhancement: Calculate base score even without faces
            # This enables scoring for landscapes, architecture, and other non-portrait images
            total_score = self._calculate_base_score(
                overall_sharpness=overall_sharpness,
                local_sharpness=local_sharpness,
                detail_score=detail_score,
                fg_bg_score=fg_bg_score,
                lighting_score=lighting_score,
                resolution_score=resolution_score,
                face_quality=face_quality,
                width=width,
                height=height
            )
            
            return QualityResult(
                path=image_path,
                face_quality=face_quality,
                overall_sharpness=overall_sharpness,
                lighting_score=lighting_score,
                resolution_score=resolution_score,
                width=width,
                height=height,
                total_score=total_score,
                camera_model=camera_model,  # PHASE 3: Added camera detection
                exif_data=exif_data,  # PHASE 3: Store EXIF for scoring
                iso_value=iso_value,  # PHASE 4 TASK 2: Sensor metadata
                aperture_value=aperture_value,  # PHASE 4 TASK 2: Sensor metadata
                focal_length=focal_length,  # PHASE 4 TASK 2: Sensor metadata
                exposure_time=exposure_time,  # PHASE 4 TASK 2: Sensor metadata
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze {image_path}: {e}")
            return QualityResult(
                path=image_path,
                error=str(e),
            )
    
    def _analyze_faces_haar(self, img: NDArray) -> FaceQuality:
        """
        Stage 1: Face + eye detection via Haar cascades (cached for performance).
        
        KEY BEHAVIOR:
        - Detects ALL faces in image
        - For EACH face, checks if eyes are open
        - Returns combined result: all_eyes_open=True ONLY if EVERY person has eyes open
        - If even ONE person has eyes closed → image disqualified
        - EARLY-EXIT: Stops analyzing after first closed eyes (hard rule)
        """
        try:
            # Early return if cascades not available
            if not self.face_cascade or not self.eye_cascade:
                logger.debug("Face/Eye cascades not loaded")
                return FaceQuality(has_face=False)
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Detect ALL faces (using CACHED cascade)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
            )
            
            # FILTER: Remove false positives by enforcing minimum face size
            # Haar Cascade kann kleine Hintergrund-Patterns als "Gesichter" erkennen
            # Mindestgröße: 350×350 Pixel (realistisch für Gruppenfotos mit 4-8 Personen)
            # Bei hochauflösenden Bildern (30MP) sind echte Gesichter typisch 400-600px
            MIN_FACE_SIZE = 350
            filtered_faces = [(x, y, w, h) for (x, y, w, h) in faces if w >= MIN_FACE_SIZE and h >= MIN_FACE_SIZE]
            
            if len(filtered_faces) < len(faces):
                logger.debug(f"❌ {len(faces) - len(filtered_faces)} False Positives gefiltert (zu klein < {MIN_FACE_SIZE}px)")
            
            logger.debug(f"Gesichtserkennung: {len(filtered_faces)} Gesichter gefunden (nach Filterung, vorher: {len(faces)})")

            if len(filtered_faces) == 0:
                logger.debug("❌ Alle erkannten Gesichter waren False Positives (zu klein)")
                return FaceQuality(has_face=False)

            # Sort by size (largest first)
            faces = sorted(filtered_faces, key=lambda f: f[2] * f[3], reverse=True)
            
            person_statuses = []
            all_eyes_open = True
            largest_person_status = None  # Cache largest face analysis
            
            # Analyze EACH detected face
            for person_id, (x, y, w, h) in enumerate(faces):
                face_region = img[y:y+h, x:x+w]
                gray_face = gray[y:y+h, x:x+w]
                face_size = w * h
                
                logger.debug(f"  👤 Person {person_id+1}: {w}×{h} Pixel")

                # Eyes detection in this face region (using CACHED cascade)
                eyes = self.eye_cascade.detectMultiScale(
                    gray_face, scaleFactor=1.1, minNeighbors=4, minSize=(15, 15)
                )
                
                eyes_open = len(eyes) >= 2
                
                logger.debug(
                    f"     → {len(eyes)} Augen gefunden → "
                    f"{'OFFEN ✅' if eyes_open else 'GESCHLOSSEN ❌'}"
                )

                # If ANY person has closed eyes → whole image fails (HARD RULE)
                if not eyes_open:
                    all_eyes_open = False
                    logger.debug(
                        f"⚠️  Person {person_id+1}: AUGEN GESCHLOSSEN → "
                        f"Gesamtes Bild wird DISQUALIFIZIERT (Early-Exit)"
                    )

                # Face sharpness for this person
                laplacian = cv2.Laplacian(gray_face, cv2.CV_64F)
                variance = laplacian.var()
                region_area = face_region.shape[0] * face_region.shape[1]
                reference_area = 250_000
                normalization_factor = np.sqrt(region_area / reference_area)
                face_sharpness = variance * normalization_factor

                # Store this person's eye status
                person_status = PersonEyeStatus(
                    person_id=person_id + 1,
                    eyes_open=eyes_open,
                    face_confidence=0.65,
                    face_size_pixels=face_size,
                    face_sharpness=face_sharpness,
                    eyes_open_score=100.0 if eyes_open else 0.0,
                    gaze_score=None,
                    head_pose_score=None,
                    smile_score=None,
                )
                person_statuses.append(person_status)
                
                # Cache first (largest) face for legacy compatibility
                if person_id == 0:
                    largest_person_status = person_status
                
                # EARLY-EXIT: If hard rule violated and we only need to know about disqualification
                if not eyes_open and AppConfig.is_debug() is False:
                    logger.info(
                        f"⚠️  Hard Rule: Person {person_id+1} hat geschlossene Augen - "
                        f"Early-Exit (no need to analyze remaining {len(faces) - person_id - 1} faces)"
                    )
                    break  # ← EARLY EXIT after hard rule violation

            logger.info(
                f"👥 Bild-Analyse abgeschlossen: {len(faces)} Personen erkannt, "
                f"alle Augen offen: {all_eyes_open}"
            )

            # Use best face for scoring
            best_person = self._select_best_person(person_statuses) or largest_person_status
            best_face_sharpness = best_person.face_sharpness if best_person else 0.0
            best_eyes_open = best_person.eyes_open if best_person else False

            return FaceQuality(
                has_face=True,
                eyes_open=best_eyes_open,  # For backward compatibility only
                all_eyes_open=all_eyes_open,  # CORRECT: True only if ALL have eyes open
                gaze_forward=True,
                head_straight=True,
                face_sharpness=best_face_sharpness,
                confidence=0.65,
                num_faces=len(faces),
                eye_count=sum(1 for p in person_statuses if p.eyes_open) * 2,  # Rough estimate
                face_count=len(faces),
                person_eye_statuses=person_statuses,
                best_person_id=best_person.person_id if best_person else 0,
                eye_open_score=best_person.eyes_open_score if best_person else None,
                gaze_forward_score=best_person.gaze_score if best_person else None,
                head_pose_score=best_person.head_pose_score if best_person else None,
                smile_score=best_person.smile_score if best_person else None,
            )

        except Exception as e:
            logger.debug(f"Face analysis failed: {e}")
            return FaceQuality(has_face=False)

    def _analyze_faces_mtcnn(self, img: NDArray) -> FaceQuality:
        """
        PHASE 2026: Modern face detection using MTCNN + MediaPipe eye analysis.
        
        Two-stage approach:
        1. MTCNN: Accurate face detection with bounding boxes (replaces Haar Cascade)
        2. MediaPipe Face Mesh: Eye analysis only on validated MTCNN faces
        
        OPTIMIZATION: Downscale image before MTCNN to reduce from 30MP to ~4MP.
        Bounding boxes are scaled back to original coordinates for accurate eye analysis.
        
        Benefits:
        - 90% fewer false positives compared to Haar Cascade
        - More accurate face localization
        - MediaPipe only runs on real faces (faster + more accurate)
        - Downscaling gives 6-10x speedup while maintaining detection accuracy
        
        Returns:
            FaceQuality with multi-person eye status
        """
        global MTCNN_AVAILABLE, _MTCNN_IMPORT_ERROR, _MTCNN_WARNING_LOGGED
        
        try:
            # Check if MTCNN is available
            if not MTCNN_AVAILABLE:
                # Log only once, not for every image
                if not _MTCNN_WARNING_LOGGED:
                    logger.debug("MTCNN not available, falling back to Haar Cascade")
                    _MTCNN_WARNING_LOGGED = True
                return self._analyze_faces_haar(img)
            
            height, width = img.shape[:2]
            
            # OPTIMIZATION: Downscale image before MTCNN (max 1600px edge)
            # Reduces 30MP to ~4MP, giving 6-10x speedup while maintaining accuracy
            MAX_EDGE = 1600
            scale_factor = 1.0
            if max(height, width) > MAX_EDGE:
                scale_factor = MAX_EDGE / max(height, width)
                new_height = int(height * scale_factor)
                new_width = int(width * scale_factor)
                img_scaled = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logger.debug(f"MTCNN: Scaled image from {width}×{height} to {new_width}×{new_height} (factor={scale_factor:.2f})")
            else:
                img_scaled = img
                logger.debug(f"MTCNN: Image already small ({width}×{height}), no scaling needed")
            
            # Convert BGR (OpenCV) to RGB (MTCNN expects RGB)
            rgb = cv2.cvtColor(img_scaled, cv2.COLOR_BGR2RGB)
            
            # STAGE 1: MTCNN Face Detection
            # Use cached detector for performance (lazy-load on first use)
            # P0 FIX: Use lock to prevent race condition when multiple threads init detector
            if self._mtcnn_detector_cache is None:
                with self._mtcnn_lock:  # P0 FIX: Thread-safe initialization
                    # Double-check pattern: another thread might have initialized it
                    if self._mtcnn_detector_cache is None:
                        try:
                            logger.debug("MTCNN: Loading detector (first use)")
                            self._mtcnn_detector_cache = MTCNN()
                        except (ImportError, RuntimeError, AttributeError, OSError, Exception) as e:
                            # TensorFlow DLL errors or other initialization issues
                            MTCNN_AVAILABLE = False
                            _MTCNN_IMPORT_ERROR = f"Init failed: {e}"
                            logger.error(f"MTCNN initialization failed ({type(e).__name__}): {e}. Falling back to Haar Cascade.")
                            return None  # Signal fallback to caller
            
            detector = self._mtcnn_detector_cache
            
            # Detect faces on scaled image (serialize inference for thread safety)
            with self._mtcnn_infer_lock:
                try:
                    detections = detector.detect_faces(rgb)
                except Exception as exc:
                    logger.error(
                        "MTCNN detect_faces failed (will reinit once): %s", exc, exc_info=True
                    )
                    # Retry once with a fresh detector in case of internal state corruption
                    try:
                        self._mtcnn_detector_cache = MTCNN()
                        detector = self._mtcnn_detector_cache
                    except Exception as reinit_exc:
                        logger.error(
                            "MTCNN reinit failed after detect_faces error: %s",
                            reinit_exc,
                            exc_info=True,
                        )
                        raise
                    detections = detector.detect_faces(rgb)
            
            if not detections:
                logger.debug("MTCNN: No faces detected")
                return FaceQuality(has_face=False)
            
            # Filter by confidence (MTCNN returns confidence score)
            MIN_CONFIDENCE = 0.90  # MTCNN is more conservative, 0.90 is reasonable
            filtered_detections = [d for d in detections if d['confidence'] >= MIN_CONFIDENCE]
            
            if not filtered_detections:
                logger.debug(f"MTCNN: All {len(detections)} faces filtered (confidence < {MIN_CONFIDENCE})")
                return FaceQuality(has_face=False)
            
            logger.debug(f"MTCNN: {len(filtered_detections)} faces detected (confidence ≥ {MIN_CONFIDENCE})")
            
            # OPTIMIZATION: Scale bounding boxes back to original image coordinates
            if scale_factor < 1.0:
                for d in filtered_detections:
                    x, y, w, h = d['box']
                    d['box'] = (int(x / scale_factor), int(y / scale_factor), int(w / scale_factor), int(h / scale_factor))
            
            # Sort by bounding box area (largest first)
            filtered_detections.sort(key=lambda d: d['box'][2] * d['box'][3], reverse=True)
            
            # STAGE 2: MediaPipe Eye Analysis on each MTCNN face
            person_statuses = []
            all_eyes_open = True
            largest_person_status = None
            
            # Get MediaPipe Face Mesh model
            face_mesh = self._get_face_mesh_model()
            if face_mesh is None:
                # Fallback: Use MTCNN confidence as proxy for "eyes open"
                # Not ideal, but better than failing completely
                if not self._face_mesh_warning_logged:
                    logger.warning("MediaPipe not available, using MTCNN-only detection (no eye analysis)")
                    self._face_mesh_warning_logged = True
                for pid, detection in enumerate(filtered_detections):
                    x, y, w, h = detection['box']
                    ps = PersonEyeStatus(
                        person_id=pid + 1,
                        eyes_open=True,  # Assume open (no eye analysis available)
                        face_confidence=detection['confidence'],
                        face_size_pixels=w * h,
                        face_sharpness=0.0,
                        eyes_open_score=100.0,
                        gaze_score=None,
                        head_pose_score=None,
                        smile_score=None,
                    )
                    person_statuses.append(ps)
                
                best_person = self._select_best_person(person_statuses)
                return FaceQuality(
                    has_face=True,
                    eyes_open=best_person.eyes_open if best_person else True,
                    all_eyes_open=True,  # No eye analysis, assume all open
                    gaze_forward=True,
                    head_straight=True,
                    face_sharpness=best_person.face_sharpness if best_person else 0.0,
                    confidence=filtered_detections[0]['confidence'] if filtered_detections else 0.0,
                    num_faces=len(filtered_detections),
                    eye_count=len(filtered_detections) * 2,
                    face_count=len(filtered_detections),
                    person_eye_statuses=person_statuses,
                    best_person_id=best_person.person_id if best_person else 0,
                    eye_open_score=best_person.eyes_open_score if best_person else None,
                    gaze_forward_score=best_person.gaze_score if best_person else None,
                    head_pose_score=best_person.head_pose_score if best_person else None,
                    smile_score=best_person.smile_score if best_person else None,
                )
            
            # MediaPipe available - analyze each MTCNN face (using original image, not scaled)
            
            for pid, detection in enumerate(filtered_detections):
                x, y, w, h = detection['box']
                
                # Ensure bounding box is within image bounds
                x = max(0, x)
                y = max(0, y)
                x2 = min(width, x + w)
                y2 = min(height, y + h)
                
                # Extract face region with padding for MediaPipe
                padding = int(max(w, h) * 0.2)  # 20% padding
                x1_pad = max(0, x - padding)
                y1_pad = max(0, y - padding)
                x2_pad = min(width, x2 + padding)
                y2_pad = min(height, y2 + padding)
                
                face_region = img[y1_pad:y2_pad, x1_pad:x2_pad]
                
                if face_region.size == 0:
                    logger.debug(f"Person {pid+1}: Empty face region, skipping")
                    continue
                
                # Convert face region to RGB for MediaPipe
                face_rgb = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)
                
                # Run MediaPipe on this face region only
                try:
                    result = face_mesh.process(face_rgb)
                    
                    if result.multi_face_landmarks and len(result.multi_face_landmarks) > 0:
                        # Get first landmark set (should be the only one in cropped region)
                        landmarks = result.multi_face_landmarks[0].landmark
                        
                        # Check eyes using Eye Aspect Ratio
                        eyes_open = self._check_eyes_open(landmarks)
                        
                        # Calculate face sharpness in region
                        face_sharpness = self._calculate_face_sharpness(
                            face_region, 
                            landmarks,
                            face_region.shape[1],
                            face_region.shape[0]
                        )

                        eyes_open_score = self._calculate_eye_openness_score(landmarks)
                        gaze_score = self._calculate_gaze_score(landmarks)
                        head_pose_score = self._calculate_head_pose_score(landmarks)
                        smile_score = self._calculate_smile_score(landmarks)
                        
                        logger.debug(
                            f"  👤 Person {pid+1}: {w}×{h}px, "
                            f"MTCNN confidence={detection['confidence']:.2f}, "
                            f"Eyes={'OPEN ✅' if eyes_open else 'CLOSED ❌'}"
                        )
                        
                        ps = PersonEyeStatus(
                            person_id=pid + 1,
                            eyes_open=eyes_open,
                            face_confidence=detection['confidence'],
                            face_size_pixels=w * h,
                            face_sharpness=face_sharpness,
                            eyes_open_score=eyes_open_score,
                            gaze_score=gaze_score,
                            head_pose_score=head_pose_score,
                            smile_score=smile_score,
                        )
                        person_statuses.append(ps)
                        
                        if pid == 0:
                            largest_person_status = ps
                        
                        if not eyes_open:
                            all_eyes_open = False
                            if AppConfig.is_debug():
                                logger.info(
                                    f"⚠️  Person {pid+1}: AUGEN GESCHLOSSEN → "
                                    f"Gesamtes Bild wird mit Malus bewertet"
                                )
                    else:
                        # MediaPipe found no landmarks in this face region
                        # Use MTCNN detection as proxy
                        logger.debug(f"Person {pid+1}: MediaPipe found no landmarks, assuming eyes open")
                        ps = PersonEyeStatus(
                            person_id=pid + 1,
                            eyes_open=True,  # Assume open if MediaPipe can't analyze
                            face_confidence=detection['confidence'],
                            face_size_pixels=w * h,
                            face_sharpness=0.0,
                            eyes_open_score=100.0,
                            gaze_score=None,
                            head_pose_score=None,
                            smile_score=None,
                        )
                        person_statuses.append(ps)
                        if pid == 0:
                            largest_person_status = ps
                            
                except Exception as e:
                    logger.debug(f"Person {pid+1}: MediaPipe analysis failed: {e}")
                    # Use MTCNN confidence as fallback
                    ps = PersonEyeStatus(
                        person_id=pid + 1,
                        eyes_open=True,  # Assume open on error
                        face_confidence=detection['confidence'],
                        face_size_pixels=w * h,
                        face_sharpness=0.0,
                        eyes_open_score=100.0,
                        gaze_score=None,
                        head_pose_score=None,
                        smile_score=None,
                    )
                    person_statuses.append(ps)
                    if pid == 0:
                        largest_person_status = ps
            
            if not person_statuses:
                logger.debug("MTCNN: No valid person statuses after MediaPipe analysis")
                return FaceQuality(has_face=False)
            
            if scale_factor < 1.0:
                logger.info(
                    f"👥 MTCNN+MediaPipe: {len(person_statuses)} Personen analysiert, "
                    f"alle Augen offen: {all_eyes_open} (detection on scaled image, analysis on full resolution)"
                )
            else:
                logger.info(
                    f"👥 MTCNN+MediaPipe: {len(person_statuses)} Personen analysiert, "
                    f"alle Augen offen: {all_eyes_open}"
                )

            best_person = self._select_best_person(person_statuses)
            best_confidence = best_person.face_confidence if best_person else 0.0
            
            return FaceQuality(
                has_face=True,
                eyes_open=best_person.eyes_open if best_person else False,
                all_eyes_open=all_eyes_open,
                gaze_forward=(best_person.gaze_score is None or best_person.gaze_score >= 60.0) if best_person else False,
                head_straight=(best_person.head_pose_score is None or best_person.head_pose_score >= 60.0) if best_person else False,
                face_sharpness=best_person.face_sharpness if best_person else 0.0,
                confidence=best_confidence,
                num_faces=len(filtered_detections),
                eye_count=sum(1 for p in person_statuses if p.eyes_open) * 2,
                face_count=len(filtered_detections),
                person_eye_statuses=person_statuses,
                best_person_id=best_person.person_id if best_person else 0,
                eye_open_score=best_person.eyes_open_score if best_person else None,
                gaze_forward_score=best_person.gaze_score if best_person else None,
                head_pose_score=best_person.head_pose_score if best_person else None,
                smile_score=best_person.smile_score if best_person else None,
            )
            
        except Exception as e:
            logger.warning(f"MTCNN face analysis failed: {e}, falling back to Haar")
            return self._analyze_faces_haar(img)

    def _analyze_faces_dlib(self, img: NDArray) -> FaceQuality:
        """Stage 2: Eye detection via dlib 68-point facial landmarks (optional).
        Requires dlib and a shape predictor .dat file. Configure path via
        env `PHOTOCLEANER_DLIB_PREDICTOR_PATH`.
        """
        try:
            if not DLIB_AVAILABLE:
                logger.debug("dlib not available")
                return FaceQuality(has_face=False)

            predictor_path = os.environ.get("PHOTOCLEANER_DLIB_PREDICTOR_PATH")
            if not predictor_path or not Path(predictor_path).exists():
                logger.debug("dlib predictor not configured or missing")
                return FaceQuality(has_face=False)

            detector = _dlib.get_frontal_face_detector()
            predictor = _dlib.shape_predictor(predictor_path)

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            rects = detector(gray, 1)
            if len(rects) == 0:
                return FaceQuality(has_face=False)

            person_statuses = []
            all_eyes_open = True
            largest_person_status = None

            def _ear(points):
                # Eye Aspect Ratio for 6 points
                # points: list of (x,y) with order 0..5
                from math import dist
                A = dist(points[1], points[5])
                B = dist(points[2], points[4])
                C = dist(points[0], points[3])
                return (A + B) / (2.0 * C + 1e-6)

            for pid, rect in enumerate(rects):
                shape = predictor(gray, rect)
                coords = [(shape.part(i).x, shape.part(i).y) for i in range(68)]
                # Left eye: 36-41, Right eye: 42-47
                left = coords[36:42]
                right = coords[42:48]
                left_ear = _ear(left)
                right_ear = _ear(right)
                ear = (left_ear + right_ear) / 2.0
                eyes_open = ear > 0.2  # Typical threshold ~0.2 for dlib EAR

                x, y, w, h = rect.left(), rect.top(), rect.width(), rect.height()
                gray_face = gray[max(0,y):max(0,y)+h, max(0,x):max(0,x)+w]
                lap = cv2.Laplacian(gray_face, cv2.CV_64F).var() if gray_face.size else 0.0
                face_size = w * h

                ps = PersonEyeStatus(
                    person_id=pid+1,
                    eyes_open=eyes_open,
                    face_confidence=0.75,
                    face_size_pixels=face_size,
                    face_sharpness=lap,
                    eyes_open_score=100.0 if eyes_open else 0.0,
                    gaze_score=None,
                    head_pose_score=None,
                    smile_score=None,
                )
                person_statuses.append(ps)
                if pid == 0:
                    largest_person_status = ps
                if not eyes_open:
                    all_eyes_open = False

            best_person = self._select_best_person(person_statuses) or largest_person_status

            return FaceQuality(
                has_face=True,
                eyes_open=best_person.eyes_open if best_person else False,
                all_eyes_open=all_eyes_open,
                gaze_forward=True,
                head_straight=True,
                face_sharpness=best_person.face_sharpness if best_person else 0.0,
                confidence=0.75,
                num_faces=len(rects),
                eye_count=sum(1 for p in person_statuses if p.eyes_open) * 2,
                face_count=len(rects),
                person_eye_statuses=person_statuses,
                best_person_id=best_person.person_id if best_person else 0,
                eye_open_score=best_person.eyes_open_score if best_person else None,
                gaze_forward_score=best_person.gaze_score if best_person else None,
                head_pose_score=best_person.head_pose_score if best_person else None,
                smile_score=best_person.smile_score if best_person else None,
            )
        except Exception as e:
            logger.debug(f"dlib face analysis failed: {e}")
            return FaceQuality(has_face=False)

    def _analyze_faces_mediapipe(self, img: NDArray) -> FaceQuality:
        """Stage 3: Eye detection via MediaPipe Face Mesh (optional).
        
        FEATURE: Uses cached model instance for 10-100x speedup vs new instance per image.
        PHASE 2: Added timeout protection for OOM scenarios in multiprocessing.
        """
        try:
            if not MEDIAPIPE_AVAILABLE:
                logger.debug("MediaPipe not available")
                return FaceQuality(has_face=False)

            height, width = img.shape[:2]
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # FEATURE: Use cached model (don't create new one for each image!)
            face_mesh = self._get_face_mesh_model()
            if face_mesh is None:
                return FaceQuality(has_face=False)
            
            # PHASE 2 FIX [TASK-3]: Timeout protection for OOM in multiprocessing
            # MediaPipe can hang in multiprocessing if GPU memory exhausted
            # Solution: Use signal-based timeout (UNIX) or thread timeout (Windows/multiprocessing safe)
            # Implementation: Wrap process() with timeout using threading
            import threading
            import queue
            
            result_queue = queue.Queue()
            error_queue = queue.Queue()
            
            def run_face_mesh():
                try:
                    result = face_mesh.process(rgb)
                    result_queue.put(result)
                except Exception as e:
                    error_queue.put(e)
            
            # Run in separate thread with 10-second timeout
            mesh_thread = threading.Thread(target=run_face_mesh, daemon=True)
            mesh_thread.start()
            mesh_thread.join(timeout=10.0)  # 10 seconds max
            
            # Check for completion
            if mesh_thread.is_alive():
                logger.warning("[PHASE-2] MediaPipe Face Mesh timeout after 10s - possible OOM in multiprocessing")
                return FaceQuality(has_face=False)  # Graceful failure
            
            # Check for errors
            if not error_queue.empty():
                e = error_queue.get()
                raise e
            
            if result_queue.empty():
                return FaceQuality(has_face=False)
            
            res = result_queue.get()
            # NOTE: Don't close the cached model - it's reused!
            landmarks_list = res.multi_face_landmarks
            if not landmarks_list:
                return FaceQuality(has_face=False)

            # FILTER: Remove false positives by checking face bounding box size
            # MediaPipe kann manchmal Hintergrund-Patterns als "Gesichter" erkennen
            # Mindestgröße: 50×50 Pixel (ca. 0.1% eines 4000×3000 Bildes)
            MIN_FACE_SIZE = 50
            filtered_landmarks = []
            
            for lm in landmarks_list:
                # Calculate bounding box from landmarks
                lm_pts = lm.landmark
                x_coords = [pt.x * width for pt in lm_pts]
                y_coords = [pt.y * height for pt in lm_pts]
                
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                face_width = x_max - x_min
                face_height = y_max - y_min
                
                # Nur Gesichter akzeptieren die größer als MIN_FACE_SIZE sind
                if face_width >= MIN_FACE_SIZE and face_height >= MIN_FACE_SIZE:
                    filtered_landmarks.append(lm)
                else:
                    logger.debug(f"❌ False Positive gefiltert: {face_width:.0f}×{face_height:.0f} Pixel (zu klein)")
            
            if not filtered_landmarks:
                logger.debug("Alle erkannten Gesichter waren False Positives (zu klein)")
                return FaceQuality(has_face=False)
            
            logger.debug(f"Gesichtserkennung: {len(filtered_landmarks)} Gesichter gefunden (nach Filterung, vorher: {len(landmarks_list)})")

            person_statuses = []
            all_eyes_open = True

            for pid, lm in enumerate(filtered_landmarks):
                lm_pts = lm.landmark
                eyes_open = self._check_eyes_open(lm_pts)
                gaze_forward = self._check_gaze_forward(lm_pts)
                head_straight = self._check_head_straight(lm_pts)
                sharp = self._calculate_face_sharpness(img, lm_pts, width, height)

                eyes_open_score = self._calculate_eye_openness_score(lm_pts)
                gaze_score = self._calculate_gaze_score(lm_pts) if gaze_forward else 0.0
                head_pose_score = self._calculate_head_pose_score(lm_pts) if head_straight else 0.0
                smile_score = self._calculate_smile_score(lm_pts)

                ps = PersonEyeStatus(
                    person_id=pid+1,
                    eyes_open=eyes_open,
                    face_confidence=0.8,
                    face_size_pixels=width*height,  # Approx (no bbox here)
                    face_sharpness=sharp,
                    eyes_open_score=eyes_open_score,
                    gaze_score=gaze_score,
                    head_pose_score=head_pose_score,
                    smile_score=smile_score,
                )
                person_statuses.append(ps)
                if not eyes_open:
                    all_eyes_open = False

            best_person = self._select_best_person(person_statuses)

            return FaceQuality(
                has_face=True,
                eyes_open=best_person.eyes_open if best_person else False,
                all_eyes_open=all_eyes_open,
                gaze_forward=(best_person.gaze_score is None or best_person.gaze_score >= 60.0) if best_person else False,
                head_straight=(best_person.head_pose_score is None or best_person.head_pose_score >= 60.0) if best_person else False,
                face_sharpness=best_person.face_sharpness if best_person else 0.0,
                confidence=0.8,
                num_faces=len(landmarks_list),
                eye_count=sum(1 for p in person_statuses if p.eyes_open) * 2,
                face_count=len(landmarks_list),
                person_eye_statuses=person_statuses,
                best_person_id=best_person.person_id if best_person else 0,
                eye_open_score=best_person.eyes_open_score if best_person else None,
                gaze_forward_score=best_person.gaze_score if best_person else None,
                head_pose_score=best_person.head_pose_score if best_person else None,
                smile_score=best_person.smile_score if best_person else None,
            )
        except Exception as e:
            logger.debug(f"MediaPipe face analysis failed: {e}")
            return FaceQuality(has_face=False)

    def _analyze_faces_progressive(self, img: NDArray) -> FaceQuality:
        """Run progressive eye detection across stages based on configuration.
        
        PHASE 2026: MTCNN replaces Haar Cascade as default Stage 1 detector.
        ENV Variable: PHOTOCLEANER_FACE_DETECTOR=mtcnn|haar (default: mtcnn)
        
        Stage progression:
        - Stage 0: No dependencies → return no face
        - Stage 1: MTCNN (modern, accurate) OR Haar Cascade (legacy fallback)
        - Stage 2: dlib 68-point landmarks (optional escalation)
        - Stage 3: MediaPipe standalone (optional, for direct MediaPipe mode)
        """
        # Handle Stage 0 (no OpenCV/dependencies available)
        if self._eye_detection_stage == 0:
            logger.debug("Keine Dependencies verfügbar, überspringe Gesichtserkennung")
            return FaceQuality(has_face=False)
        
        # Check which face detector to use (MTCNN or Haar)
        face_detector = os.environ.get("PHOTOCLEANER_FACE_DETECTOR", "mtcnn").lower()
        
        # Stage 1: Face Detection (MTCNN or Haar)
        if face_detector == "mtcnn" and MTCNN_AVAILABLE:
            logger.debug("Using MTCNN for face detection (modern, accurate)")
            result = self._analyze_faces_mtcnn(img)
            
            # If MTCNN returned None (initialization failed), fall back to Haar
            if result is None:
                logger.warning("MTCNN initialization failed at runtime, falling back to Haar Cascade")
                result = self._analyze_faces_haar(img)
        else:
            # Fallback to Haar Cascade
            if face_detector == "mtcnn" and not MTCNN_AVAILABLE:
                # Log only once per session, not for every image
                global _MTCNN_WARNING_LOGGED
                if _MTCNN_IMPORT_ERROR and not _MTCNN_WARNING_LOGGED:
                    logger.warning(f"MTCNN: Import failed - {_MTCNN_IMPORT_ERROR}")
                    _MTCNN_WARNING_LOGGED = True
                elif not _MTCNN_WARNING_LOGGED:
                    logger.warning("MTCNN requested but not available, falling back to Haar Cascade")
                    _MTCNN_WARNING_LOGGED = True
            logger.debug("Using Haar Cascade for face detection (legacy)")
            result = self._analyze_faces_haar(img)
        
        if self._eye_detection_stage <= 1:
            return result

        # Escalate if uncertain or failed (and Stage 2 is available)
        need_escalate = (not result.has_face) or (not result.all_eyes_open)
        if self._eye_detection_stage >= 2 and need_escalate:
            # Double-check dlib is actually available (should be if stage=2)
            if not DLIB_AVAILABLE:
                # Log only once at DEBUG level to avoid spam
                logger.debug("Stufe 2 konfiguriert, aber dlib nicht verfügbar")
                return result
            
            logger.debug("Escalating to dlib (Stage 2) for improved eye detection...")
            dl = self._analyze_faces_dlib(img)
            if dl.has_face and dl.all_eyes_open:
                return dl
            # If dlib found faces but still closed eyes, prefer dlib result
            if dl.has_face:
                result = dl

        # Escalate to Stage 3 if needed (and available)
        if self._eye_detection_stage >= 3 and ((not result.has_face) or (not result.all_eyes_open)):
            # Double-check MediaPipe is actually available
            if not MEDIAPIPE_AVAILABLE:
                logger.warning("Stufe 3 konfiguriert, aber MediaPipe nicht verfügbar")
                return result
            
            logger.debug("Escalating to MediaPipe Face Mesh (Stage 3) for maximal accuracy...")
            mpres = self._analyze_faces_mediapipe(img)
            if mpres.has_face:
                return mpres
        
        return result
    
    def _calculate_sharpness_fft(self, gray: NDArray) -> float:
        """
        Calculate sharpness using FFT high-frequency energy ratio.
        
        Returns a 0-100 score where higher means sharper.
        """
        try:
            if gray is None or gray.size == 0:
                return 0.0
            
            # Compute FFT and magnitude spectrum
            f = np.fft.fft2(gray)
            fshift = np.fft.fftshift(f)
            magnitude = np.abs(fshift)
            
            if magnitude.size == 0:
                return 0.0
            
            h, w = gray.shape[:2]
            cy, cx = h // 2, w // 2
            radius = int(min(h, w) * 0.1)  # low-frequency radius
            
            # Mask for low frequencies (center circle)
            y, x = np.ogrid[:h, :w]
            mask = (y - cy) ** 2 + (x - cx) ** 2 <= radius ** 2
            
            low_freq_energy = magnitude[mask].sum()
            total_energy = magnitude.sum()
            if total_energy == 0:
                return 0.0
            
            high_freq_energy = total_energy - low_freq_energy
            ratio = high_freq_energy / total_energy
            
            # Scale to 0-100
            return float(min(100.0, max(0.0, ratio * 100.0)))
        except Exception as e:
            logger.debug(f"FFT sharpness calculation failed: {e}")
            return 0.0

    def _calculate_local_sharpness(self, gray: NDArray) -> float:
        """
        Week 5: Local sharpness consistency using tile-based Laplacian.
        Returns a 0-100 score where higher means more consistently sharp.
        """
        try:
            if gray is None or gray.size == 0:
                return 0.0

            h, w = gray.shape[:2]
            if h < 64 or w < 64:
                return self._calculate_sharpness_fft(gray)

            tiles_y = 3
            tiles_x = 3
            tile_h = h // tiles_y
            tile_w = w // tiles_x
            scores = []

            for ty in range(tiles_y):
                for tx in range(tiles_x):
                    y0 = ty * tile_h
                    x0 = tx * tile_w
                    y1 = h if ty == tiles_y - 1 else y0 + tile_h
                    x1 = w if tx == tiles_x - 1 else x0 + tile_w
                    tile = gray[y0:y1, x0:x1]
                    if tile.size == 0:
                        continue
                    var = cv2.Laplacian(tile, cv2.CV_64F).var()
                    # Normalize similar to legacy scale
                    score = min(100.0, (var / 400.0) * 100.0)
                    scores.append(score)

            if not scores:
                return self._calculate_sharpness_fft(gray)

            # Penalize inconsistency: average minus std deviation
            avg = float(np.mean(scores))
            std = float(np.std(scores))
            local_score = max(0.0, min(100.0, avg - std))

            if AppConfig.is_debug():
                logger.debug(f"LocalSharpness: avg={avg:.1f} std={std:.1f} score={local_score:.1f}")

            return local_score
        except Exception as e:
            logger.debug(f"Local sharpness calculation failed: {e}")
            return self._calculate_sharpness_fft(gray)

    def _calculate_detail_score(self, gray: NDArray) -> float:
        """
        Week 5: Detail scoring using texture/edge density.
        Returns 0-100 where higher means richer detail.
        """
        try:
            if gray is None or gray.size == 0:
                return 0.0

            # Edge density (Sobel magnitude)
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            mag = np.sqrt(grad_x ** 2 + grad_y ** 2)
            edge_strength = float(np.mean(mag))

            # Texture via Laplacian variance
            texture = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            # Normalize to 0-100
            edge_score = min(100.0, (edge_strength / 50.0) * 100.0)
            texture_score = min(100.0, (texture / 400.0) * 100.0)

            detail_score = max(0.0, min(100.0, edge_score * 0.6 + texture_score * 0.4))

            if AppConfig.is_debug():
                logger.debug(
                    f"DetailScore: edge={edge_score:.1f} texture={texture_score:.1f} "
                    f"score={detail_score:.1f}"
                )

            return detail_score
        except Exception as e:
            logger.debug(f"Detail score calculation failed: {e}")
            return 0.0

    def _calculate_foreground_background_score(self, gray: NDArray) -> float:
        """
        Foreground/Background separation score based on center vs edge sharpness.
        Higher score if center is sharper than edges (subject separation).
        """
        try:
            if gray is None or gray.size == 0:
                return 0.0

            h, w = gray.shape[:2]
            if h < 64 or w < 64:
                return 0.0

            # Define center region (subject area)
            ch, cw = int(h * 0.5), int(w * 0.5)
            y0 = (h - ch) // 2
            x0 = (w - cw) // 2
            center = gray[y0:y0 + ch, x0:x0 + cw]

            # Edge region mask (background area)
            edge_mask = np.ones_like(gray, dtype=bool)
            edge_mask[y0:y0 + ch, x0:x0 + cw] = False
            edges = gray[edge_mask]

            if center.size == 0 or edges.size == 0:
                return 0.0

            # Sharpness via Laplacian variance
            center_var = float(cv2.Laplacian(center, cv2.CV_64F).var())
            edge_var = float(cv2.Laplacian(edges, cv2.CV_64F).var())

            # Ratio of center sharpness to edge sharpness
            ratio = (center_var + 1e-6) / (edge_var + 1e-6)
            # Map ratio to 0-100 with diminishing returns
            score = min(100.0, max(0.0, (ratio - 0.5) * 40.0))

            if AppConfig.is_debug():
                logger.debug(
                    f"FG/BG: center_var={center_var:.1f} edge_var={edge_var:.1f} "
                    f"ratio={ratio:.2f} score={score:.1f}"
                )

            return score
        except Exception as e:
            logger.debug(f"Foreground/background calculation failed: {e}")
            return 0.0

    def _calculate_motion_blur_penalty(
        self, sharpness_normalized: float, local_sharpness: float
    ) -> float:
        """
        Motion blur penalty (0-20). Higher when sharpness is low overall.
        """
        # Penalize strongly if global sharpness is low
        if sharpness_normalized >= 60:
            return 0.0
        # Scale penalty for low sharpness
        penalty = (60.0 - sharpness_normalized) * 0.3
        return min(20.0, max(0.0, penalty))

    def _calculate_autofocus_penalty(
        self, sharpness_normalized: float, local_sharpness: float
    ) -> float:
        """
        Autofocus error penalty (0-15). Higher when local sharpness is
        much lower than global sharpness (inconsistent focus).
        """
        diff = sharpness_normalized - local_sharpness
        if diff <= 5:
            return 0.0
        penalty = diff * 0.3
        return min(15.0, max(0.0, penalty))
    
    def _calculate_lighting_score(self, gray: NDArray) -> float:
        """Calculate lighting quality score (0-100) based on histogram analysis.
        
        BUG-L3 FIX: Comprehensive docstring explaining scoring algorithm.
        BUG-M1 FIX: Uses ScoringConstants for all threshold values.
        BUG-H3 FIX: Includes empty image/histogram protection.
        
        Evaluates three aspects of lighting quality:
        1. Brightness: Ideal range is 110-140 (slightly bright)
        2. Contrast: Good contrast has std deviation > 40
        3. Clipping: Penalizes over/underexposed pixels
        
        Scoring formula:
        - Base score: 50% brightness + 50% contrast
        - Penalty: Subtract percentage of clipped pixels (too dark/bright)
        - Range: Clamped to 0-100
        
        Args:
            gray: Grayscale image array (numpy ndarray, single channel)
            
        Returns:
            Lighting quality score (0-100)
            - 100: Perfect exposure and contrast
            - 50: Neutral (fallback for errors or empty images)
            - 0: Severely under/overexposed or no contrast
            
        Note:
            Returns 50.0 (neutral) if image is empty or histogram cannot be computed.
        """
        try:
            # BUG-H3 FIX: Check for empty or invalid images before processing
            if gray.size == 0:
                logger.warning("Empty image array, using neutral lighting score")
                return 50.0
            
            # Calculate histogram
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            
            # BUG-H3 FIX: Check histogram sum before division to prevent division by zero
            hist_sum = hist.sum()
            if hist_sum == 0:
                logger.warning("Empty histogram (all-black image), using neutral lighting score")
                return 50.0
            
            hist = hist.flatten() / hist_sum  # Normalize
            
            # Calculate mean brightness
            mean_brightness = np.mean(gray)
            
            # Calculate contrast (std deviation)
            contrast = np.std(gray)
            
            # Ideal brightness: centered around 125 (slightly bright)
            brightness_score = 100 * (
                1 - min(
                    abs(mean_brightness - ScoringConstants.LIGHTING_IDEAL_BRIGHTNESS_CENTER) 
                    / ScoringConstants.LIGHTING_IDEAL_BRIGHTNESS_CENTER, 
                    1.0
                )
            )
            
            # Good contrast: > 40
            contrast_score = min(contrast / ScoringConstants.LIGHTING_CONTRAST_REFERENCE, 1.0) * 100
            
            # Check for clipping (over/underexposure)
            dark_pixels = np.sum(gray < ScoringConstants.LIGHTING_DARK_PIXEL_THRESHOLD) / gray.size
            bright_pixels = np.sum(gray > ScoringConstants.LIGHTING_BRIGHT_PIXEL_THRESHOLD) / gray.size
            clipping_penalty = (dark_pixels + bright_pixels) * 100
            
            # HDR/Exposure balance score (0-100)
            exposure_balance_score = self._calculate_exposure_balance(gray)

            # Combined score (Week 4: HDR/Exposure Optimization)
            lighting_score = (
                brightness_score * 0.4 +
                contrast_score * 0.4 +
                exposure_balance_score * 0.2
            ) - clipping_penalty
            lighting_score = max(0, min(100, lighting_score))
            
            # BUG-M2 FIX: Use debug level for detailed scoring (only in DEBUG mode)
            if AppConfig.is_debug():
                logger.debug(
                    f"Lighting: Brightness={mean_brightness:.1f} Contrast={contrast:.1f} "
                    f"Exposure={exposure_balance_score:.1f} Score={lighting_score:.1f}"
                )
            
            return lighting_score
        except Exception as e:
            logger.warning(f"Lighting calculation failed: {e}")
            return 50.0  # Neutral default

    def _calculate_color_cast_penalty(self, bgr: NDArray) -> float:
        """
        Penalize strong color casts (overly green/blue/red tint).
        Returns a penalty (0-20) that is subtracted from lighting score.
        """
        try:
            if bgr is None or bgr.size == 0:
                return 0.0
            # Compute mean per channel (OpenCV uses BGR)
            b_mean = float(np.mean(bgr[:, :, 0]))
            g_mean = float(np.mean(bgr[:, :, 1]))
            r_mean = float(np.mean(bgr[:, :, 2]))
            avg = (b_mean + g_mean + r_mean) / 3.0
            if avg == 0:
                return 0.0

            # Average absolute deviation from neutral gray
            deviation = (abs(b_mean - avg) + abs(g_mean - avg) + abs(r_mean - avg)) / 3.0
            deviation_ratio = deviation / avg

            # Scale to 0-20 penalty
            penalty = min(20.0, deviation_ratio * 100.0)

            if AppConfig.is_debug() and penalty > 0:
                logger.debug(
                    f"ColorCast: B={b_mean:.1f} G={g_mean:.1f} R={r_mean:.1f} "
                    f"Penalty={penalty:.1f}"
                )
            return penalty
        except Exception as e:
            logger.debug(f"Color cast calculation failed: {e}")
            return 0.0

    def _calculate_exposure_balance(self, gray: NDArray) -> float:
        """
        HDR/Exposure Optimization: Evaluate shadow/highlight balance.

        Returns a 0-100 score where higher means better dynamic range usage.
        Penalizes crushed shadows and blown highlights.
        """
        try:
            if gray is None or gray.size == 0:
                return 50.0

            # Percentiles for shadow/highlight analysis
            p5 = float(np.percentile(gray, 5))
            p50 = float(np.percentile(gray, 50))
            p95 = float(np.percentile(gray, 95))

            # Shadow penalty if very dark lower tail
            shadow_penalty = max(0.0, (20.0 - p5)) * 2.0
            # Highlight penalty if very bright upper tail
            highlight_penalty = max(0.0, (p95 - 235.0)) * 2.0

            # Midtone balance: penalize if median is too dark/bright
            midtone_penalty = abs(p50 - 128.0) * 0.2

            score = 100.0 - (shadow_penalty + highlight_penalty + midtone_penalty)
            score = max(0.0, min(100.0, score))

            if AppConfig.is_debug():
                logger.debug(
                    f"ExposureBalance: p5={p5:.1f} p50={p50:.1f} p95={p95:.1f} "
                    f"Score={score:.1f}"
                )

            return score
        except Exception as e:
            logger.debug(f"Exposure balance calculation failed: {e}")
            return 50.0
    
    def _normalize_face_sharpness_score(self, face_sharpness: float) -> float:
        """Normalize face sharpness to a 0-100 score."""
        if face_sharpness <= 0:
            return 0.0
        reference = ScoringConstants.FACE_SHARPNESS_REFERENCE
        return max(0.0, min(100.0, (face_sharpness / reference) * 100.0))

    def _calculate_eye_openness_score(self, landmarks) -> float:
        """Return eye openness score (0-100) using EAR."""
        left_top = landmarks[159].y
        left_bottom = landmarks[145].y
        right_top = landmarks[386].y
        right_bottom = landmarks[374].y
        ear = (abs(left_top - left_bottom) + abs(right_top - right_bottom)) / 2.0
        score = (ear - ScoringConstants.EAR_SCORE_MIN) / (
            ScoringConstants.EAR_SCORE_MAX - ScoringConstants.EAR_SCORE_MIN
        )
        return max(0.0, min(100.0, score * 100.0))

    def _calculate_gaze_score(self, landmarks) -> float:
        """Return eye contact score (0-100) based on iris centering."""
        left_iris = landmarks[468].x if len(landmarks) > 468 else landmarks[33].x
        left_inner = landmarks[133].x
        left_outer = landmarks[33].x
        right_iris = landmarks[473].x if len(landmarks) > 473 else landmarks[362].x
        right_inner = landmarks[362].x
        right_outer = landmarks[263].x

        left_center = (left_inner + left_outer) / 2.0
        right_center = (right_inner + right_outer) / 2.0
        left_dev = abs(left_iris - left_center)
        right_dev = abs(right_iris - right_center)
        avg_dev = (left_dev + right_dev) / 2.0

        score = 1.0 - (avg_dev / ScoringConstants.GAZE_MAX_DEVIATION)
        return max(0.0, min(100.0, score * 100.0))

    def _calculate_head_pose_score(self, landmarks) -> float:
        """Return head pose score (0-100) based on tilt and yaw proxies."""
        nose_top = landmarks[168]
        nose_bottom = landmarks[2]
        left_cheek = landmarks[234]
        right_cheek = landmarks[454]

        nose_angle = abs(nose_top.x - nose_bottom.x)
        face_tilt = abs(left_cheek.y - right_cheek.y)
        deviation = max(nose_angle, face_tilt)
        score = 1.0 - (deviation / ScoringConstants.HEAD_TILT_MAX_DEVIATION)
        return max(0.0, min(100.0, score * 100.0))

    def _calculate_smile_score(self, landmarks) -> float:
        """Return smile score (0-100) using mouth aspect ratio."""
        left_corner = landmarks[61]
        right_corner = landmarks[291]
        upper_lip = landmarks[13]
        lower_lip = landmarks[14]

        mouth_width = abs(left_corner.x - right_corner.x)
        mouth_height = abs(upper_lip.y - lower_lip.y)
        ratio = mouth_width / (mouth_height + 1e-6)

        score = (ratio - ScoringConstants.SMILE_RATIO_MIN) / (
            ScoringConstants.SMILE_RATIO_MAX - ScoringConstants.SMILE_RATIO_MIN
        )
        return max(0.0, min(100.0, score * 100.0))

    def _select_best_person(self, person_statuses: list[PersonEyeStatus]) -> Optional[PersonEyeStatus]:
        """Select best person among multiple faces based on quality signals."""
        if not person_statuses:
            return None

        max_face_size = max(p.face_size_pixels for p in person_statuses) or 1

        def score_person(ps: PersonEyeStatus) -> float:
            size_score = ps.face_size_pixels / max_face_size
            confidence_score = ps.face_confidence
            eyes_score = (
                ps.eyes_open_score / 100.0
                if ps.eyes_open_score is not None
                else (1.0 if ps.eyes_open else 0.3)
            )
            sharpness_score = (
                self._normalize_face_sharpness_score(ps.face_sharpness) / 100.0
                if ps.face_sharpness is not None
                else 0.0
            )
            gaze_score = (ps.gaze_score / 100.0) if ps.gaze_score is not None else 0.5
            head_score = (ps.head_pose_score / 100.0) if ps.head_pose_score is not None else 0.5
            smile_score = (ps.smile_score / 100.0) if ps.smile_score is not None else 0.5

            return (
                size_score * 0.25
                + confidence_score * 0.15
                + eyes_score * 0.25
                + sharpness_score * 0.15
                + gaze_score * 0.10
                + head_score * 0.10
                + smile_score * 0.10
            )

        return max(person_statuses, key=score_person)

    def _calculate_face_quality_score(self, face_quality: FaceQuality) -> float:
        """Calculate face-based score (0-100) using detailed face metrics."""
        if not face_quality or not face_quality.has_face:
            return ScoringConstants.FACE_QUALITY_NO_FACE_NEUTRAL

        eye_score = (
            face_quality.eye_open_score
            if face_quality.eye_open_score is not None
            else (100.0 if face_quality.all_eyes_open else ScoringConstants.FACE_QUALITY_CLOSED_EYES_MALUS)
        )
        sharpness_score = self._normalize_face_sharpness_score(face_quality.face_sharpness)
        gaze_score = face_quality.gaze_forward_score
        head_pose_score = face_quality.head_pose_score
        smile_score = face_quality.smile_score

        scores = {
            "eyes": eye_score,
            "sharpness": sharpness_score,
            "gaze": gaze_score,
            "head_pose": head_pose_score,
            "smile": smile_score,
        }
        weights = {
            "eyes": ScoringConstants.FACE_SCORE_WEIGHT_EYES,
            "sharpness": ScoringConstants.FACE_SCORE_WEIGHT_SHARPNESS,
            "gaze": ScoringConstants.FACE_SCORE_WEIGHT_GAZE,
            "head_pose": ScoringConstants.FACE_SCORE_WEIGHT_HEAD_POSE,
            "smile": ScoringConstants.FACE_SCORE_WEIGHT_SMILE,
        }

        total_weight = 0.0
        weighted_sum = 0.0
        for key, value in scores.items():
            if value is None:
                continue
            weighted_sum += value * weights[key]
            total_weight += weights[key]

        if total_weight == 0.0:
            face_score = ScoringConstants.FACE_QUALITY_BASE_SCORE
        else:
            face_score = weighted_sum / total_weight

        if not face_quality.all_eyes_open:
            face_score = min(face_score, ScoringConstants.FACE_QUALITY_CLOSED_EYES_MALUS)

        face_score = min(100.0, face_score + face_quality.confidence * ScoringConstants.FACE_QUALITY_CONFIDENCE_BOOST)
        return max(0.0, min(100.0, face_score))

    def _check_eyes_open(self, landmarks) -> bool:
        """
        Check if eyes are open using Eye Aspect Ratio.
        
        MediaPipe Face Mesh landmark indices:
        - Left eye: 33, 160, 158, 133, 153, 144
        - Right eye: 362, 385, 387, 263, 373, 380
        """
        # Left eye vertical distances
        left_top = landmarks[159].y
        left_bottom = landmarks[145].y
        left_ear = abs(left_top - left_bottom)
        
        # Right eye vertical distances
        right_top = landmarks[386].y
        right_bottom = landmarks[374].y
        right_ear = abs(right_top - right_bottom)
        
        # Average EAR
        ear = (left_ear + right_ear) / 2
        
        # Threshold (typical open eye has EAR > 0.02)
        return ear > ScoringConstants.EAR_THRESHOLD_MEDIAPIPE
    
    def _check_gaze_forward(self, landmarks) -> bool:
        """
        Check if gaze is forward (not looking away).
        
        Uses iris positions relative to eye corners.
        """
        # Left iris center (landmark 468)
        left_iris = landmarks[468].x if len(landmarks) > 468 else landmarks[33].x
        left_inner = landmarks[133].x
        left_outer = landmarks[33].x
        
        # Right iris center (landmark 473)
        right_iris = landmarks[473].x if len(landmarks) > 473 else landmarks[362].x
        right_inner = landmarks[362].x
        right_outer = landmarks[263].x
        
        # Check if iris is centered (with tolerance)
        left_centered = abs(left_iris - (left_inner + left_outer) / 2) < ScoringConstants.GAZE_CENTER_TOLERANCE
        right_centered = abs(right_iris - (right_inner + right_outer) / 2) < ScoringConstants.GAZE_CENTER_TOLERANCE
        
        return left_centered and right_centered
    
    def _check_head_straight(self, landmarks) -> bool:
        """
        Check if head is straight (not tilted).
        
        Uses nose bridge and face outline angles.
        """
        # Nose bridge points
        nose_top = landmarks[168]
        nose_bottom = landmarks[2]
        
        # Face outline points
        left_cheek = landmarks[234]
        right_cheek = landmarks[454]
        
        # Calculate angles
        nose_angle = abs(nose_top.x - nose_bottom.x)
        face_tilt = abs(left_cheek.y - right_cheek.y)
        
        # Threshold for straightness
        return nose_angle < ScoringConstants.HEAD_TILT_ANGLE_TOLERANCE and face_tilt < ScoringConstants.HEAD_TILT_ANGLE_TOLERANCE
    
    def _calculate_face_sharpness(
        self, img: NDArray, landmarks, width: int, height: int
    ) -> float:
        """
        Calculate sharpness in face region.
        
        Args:
            img: OpenCV image
            landmarks: Face landmarks
            width: Image width
            height: Image height
            
        Returns:
            Sharpness score (Laplacian variance, normalized by region area)
        """
        # Get face bounding box
        x_coords = [lm.x * width for lm in landmarks]
        y_coords = [lm.y * height for lm in landmarks]
        
        x_min = max(0, int(min(x_coords)) - 20)
        x_max = min(width, int(max(x_coords)) + 20)
        y_min = max(0, int(min(y_coords)) - 20)
        y_max = min(height, int(max(y_coords)) + 20)
        
        # Extract face region
        face_region = img[y_min:y_max, x_min:x_max]
        
        if face_region.size == 0:
            return 0.0
        
        # Calculate sharpness in face region
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray_face, cv2.CV_64F)
        variance = laplacian.var()
        
        # BUGFIX: Normalize by region area to make dimension-independent
        # Without this, portrait and landscape faces get different scores
        # even with identical sharpness due to different aspect ratios.
        # 
        # Explanation: Laplacian variance is affected by edge distribution
        # across the region. A 500×700 region produces different variance
        # than a 700×500 region (same area, different proportions).
        # 
        # Normalization formula: var * sqrt(area / reference_area)
        # Reference: 500×500 = 250,000 pixels (typical face region)
        region_area = face_region.shape[0] * face_region.shape[1]
        reference_area = ScoringConstants.SHARPNESS_REFERENCE_FACE_AREA
        normalization_factor = np.sqrt(region_area / reference_area)
        
        sharpness = variance * normalization_factor
        
        return sharpness
    
    # NOTE [BUG-C1 & BUG-L1]: Score calculation moved entirely to AutoSelector._score_image()
    # This ensures single source of truth for image quality scoring.
    # See auto_selector.py for the scoring logic (55% eyes, 20% sharpness, 15% lighting, 10% resolution)
    # Rationale: Duplicate code path led to inconsistencies and maintenance burden
    
    def analyze_batch(
        self,
        image_paths: list[Path],
        progress_callback: Optional[callable] = None,
        max_workers: int = 4,
    ) -> list[QualityResult]:
        """
        Analyze multiple images using ThreadPool for parallelization.
        
        Args:
            image_paths: List of image paths
            progress_callback: Optional callback for progress updates
            max_workers: Number of parallel threads (default: 4)
            
        Returns:
            List of QualityResults
        """
        logger.info(f"=== QualityAnalyzer.analyze_batch() STARTED ===")
        logger.info(f"Analyzing {len(image_paths)} images with {max_workers} workers (ThreadPool)...")
        logger.info(f"use_face_mesh: {self.use_face_mesh}")
        
        results = [None] * len(image_paths)  # Pre-allocate for correct ordering
        processed_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks and create mapping of future -> index
            future_to_index = {
                executor.submit(self.analyze_image, path): idx
                for idx, path in enumerate(image_paths)
            }
            
            # Process results as they complete
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                    results[idx] = result
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error analyzing {image_paths[idx]}: {e}", exc_info=True)
                    results[idx] = QualityResult(
                        path=image_paths[idx],
                        error=str(e),
                        quality_score=0.0,
                    )
                    processed_count += 1
                
                # Progress callback
                if progress_callback:
                    try:
                        progress_callback(processed_count, len(image_paths))
                    except (TypeError, AttributeError):
                        logger.debug("Progress callback error", exc_info=True)
                
                # Log progress more frequently for better feedback
                if processed_count % 5 == 0 or processed_count == len(image_paths):
                    logger.info(f"Analyzed {processed_count}/{len(image_paths)} images")
        
        logger.info(f"=== QualityAnalyzer.analyze_batch() COMPLETED ===")
        logger.info(f"Analyzed {len(results)} images, {sum(1 for r in results if r.error is None)} successful")
        return results
