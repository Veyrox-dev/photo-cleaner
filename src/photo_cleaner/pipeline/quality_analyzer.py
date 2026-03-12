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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from photo_cleaner.pipeline.analysis import CameraProfile, ExifExtractor, FaceQuality, PersonEyeStatus, QualityResult, QualityScorer
from photo_cleaner.pipeline.analysis.face_mesh_resolver import resolve_face_mesh_ctor
from photo_cleaner.pipeline.analysis.haar_cascade_resolver import resolve_haar_cascade_dir
import photo_cleaner.pipeline.analysis.face_detector as face_detector_module
from photo_cleaner.pipeline.analysis.face_detector import FaceDetector

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
    return resolve_face_mesh_ctor(mediapipe_available=MEDIAPIPE_AVAILABLE, mp_module=_mp)


def _resolve_haar_cascade_dir() -> Path | None:
    return resolve_haar_cascade_dir(cv2_available=CV2_AVAILABLE, cv2_module=_cv2)


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
        
        # Haar cascades are managed inside FaceDetector (single source of truth)
        self.face_cascade = None
        self.eye_cascade = None
        logger.debug("[INIT] Haar cascades delegated to FaceDetector")

        # Sync lazily-loaded dependency state into face detector module
        face_detector_module.CV2_AVAILABLE = CV2_AVAILABLE
        face_detector_module.MEDIAPIPE_AVAILABLE = MEDIAPIPE_AVAILABLE
        face_detector_module.DLIB_AVAILABLE = DLIB_AVAILABLE
        face_detector_module.MTCNN_AVAILABLE = MTCNN_AVAILABLE
        face_detector_module.cv2 = _cv2
        face_detector_module.np = _np
        face_detector_module.MTCNN = _MTCNN
        face_detector_module._dlib = _dlib
        face_detector_module._mp = _mp
        
        # Create FaceDetector instance (handles all face detection strategies)
        logger.debug("[INIT] Initializing FaceDetector...")
        self.face_detector = FaceDetector(
            eye_detection_stage=self._eye_detection_stage,
            min_tracking_confidence=min_tracking_confidence
        )
        logger.debug("[INIT] FaceDetector initialized")
        
        # Create QualityScorer instance (handles all quality scoring)
        logger.debug("[INIT] Initializing QualityScorer...")
        self.quality_scorer = QualityScorer(np_module=_np, cv2_module=_cv2)
        logger.debug("[INIT] QualityScorer initialized")

        # Create ExifExtractor instance (handles EXIF parsing and orientation)
        logger.debug("[INIT] Initializing ExifExtractor...")
        self.exif_extractor = ExifExtractor(image_module=_Image, cv2_module=_cv2)
        logger.debug("[INIT] ExifExtractor initialized")
        
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
        """Compatibility wrapper around ExifExtractor orientation handling."""
        return self.exif_extractor.get_exif_orientation_from_pil(pil_image, image_path)
    
    def _extract_exif_data_from_pil(self, pil_image, image_path: Path) -> dict:
        """Compatibility wrapper around ExifExtractor EXIF parsing."""
        return self.exif_extractor.extract_exif_data_from_pil(pil_image, image_path)
    
    def _extract_exif_data(self, image_path: Path) -> dict:
        """PHASE 3 TASK 1: Extract EXIF data for camera model detection.
        PHASE 4 TASK 2: Extended to include sensor metadata (ISO, Aperture, Focal Length, Exposure).
        
        DEPRECATED: Now delegates to _extract_exif_data_from_pil() for consistency.
        
        Returns:
            Dictionary with EXIF fields including camera model and sensor metadata or empty dict if not available
        """
        return self.exif_extractor.extract_exif_data(image_path)
    
    def _rotate_image_from_exif(self, img: NDArray, orientation: int) -> NDArray:
        """Compatibility wrapper around ExifExtractor rotation handling."""
        return self.exif_extractor.rotate_image_from_exif(img, orientation)
    
    # NOTE [BUG-C1 & BUG-L1]: Score calculation moved entirely to AutoSelector._score_image()
    # This ensures single source of truth for image quality scoring.
    # See auto_selector.py for the scoring logic (55% eyes, 20% sharpness, 15% lighting, 10% resolution)
    # Rationale: Duplicate code path led to inconsistencies and maintenance burden
    
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
            overall_sharpness = self.quality_scorer.calculate_sharpness_fft(gray)
            local_sharpness = self.quality_scorer.calculate_local_sharpness(gray)
            detail_score = self.quality_scorer.calculate_detail_score(gray)
            fg_bg_score = self.quality_scorer.calculate_foreground_background_score(gray)
            
            # Calculate lighting score (0-100 based on histogram)
            lighting_score = self.quality_scorer.calculate_lighting_score(gray)
            # Week 3: Apply color cast penalty (green/magenta/blue tint)
            lighting_score = max(0.0, lighting_score - self.quality_scorer.calculate_color_cast_penalty(img))
            
            # Progressive eye detection: Haar → dlib (optional) → MediaPipe (optional)
            try:
                face_quality = self.face_detector.analyze_faces(img)
            except Exception as e:
                logger.exception(f"Face analysis failed for {image_path.name}")
                # Fallback: Return neutral score (no face detected)
                face_quality = FaceQuality(has_face=False)
            
            # Phase 3 Enhancement: Calculate base score even without faces
            # This enables scoring for landscapes, architecture, and other non-portrait images
            total_score = self.quality_scorer.calculate_base_score(
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
