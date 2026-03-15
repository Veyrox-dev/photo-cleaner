"""
Quality Analyzer with MTCNN + MediaPipe.

Expensive quality analysis for duplicate groups.
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from photo_cleaner.config import AppConfig
from photo_cleaner.pipeline.analysis import CameraProfile, ExifExtractor, FaceQuality, PersonEyeStatus, QualityResult, QualityScorer
from photo_cleaner.pipeline.analysis.analysis_executor import execute_quality_analysis
from photo_cleaner.pipeline.analysis.batch_runner import run_quality_batch
from photo_cleaner.pipeline.analysis.capability_resolver import build_stage_info, determine_available_eye_stage
import photo_cleaner.pipeline.analysis.face_detector as face_detector_module
from photo_cleaner.pipeline.analysis.face_detector import FaceDetector
from photo_cleaner.pipeline.analysis.haar_cascade_resolver import resolve_haar_cascade_dir
from photo_cleaner.pipeline.analysis.image_preprocessor import prepare_image_for_quality_analysis
from photo_cleaner.pipeline.analysis.metadata_enricher import enrich_image_with_metadata
from photo_cleaner.pipeline.analysis.runtime_dependencies import (
    ensure_runtime_dependencies,
    get_runtime_dependency_snapshot,
    mark_mtcnn_unavailable,
)
from photo_cleaner.pipeline.scoring_constants import ScoringConstants  # BUG-M1 FIX

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


# Runtime dependency aliases populated by _ensure_dependencies()
_cv2 = None
_np = None
_Image = None
_mp = None
_dlib = None
_MTCNN = None

CV2_AVAILABLE = True
MEDIAPIPE_AVAILABLE = True
DLIB_AVAILABLE = True
MTCNN_AVAILABLE = True
_MTCNN_IMPORT_ERROR = None
_MTCNN_WARNING_LOGGED = False
_MEDIAPIPE_IMPORT_ERROR = None
_MEDIAPIPE_DRAWING_DISABLED = False

logger = logging.getLogger(__name__)


def _sync_runtime_dependency_snapshot() -> None:
    """Sync module-level compatibility aliases from shared runtime dependency state."""
    global _cv2, _np, _Image, _mp, _dlib, _MTCNN
    global CV2_AVAILABLE, MEDIAPIPE_AVAILABLE, DLIB_AVAILABLE, MTCNN_AVAILABLE
    global _MTCNN_IMPORT_ERROR, _MEDIAPIPE_IMPORT_ERROR, _MEDIAPIPE_DRAWING_DISABLED
    global cv2, np, Image, MTCNN

    snapshot = get_runtime_dependency_snapshot()
    _cv2 = snapshot.cv2_module
    _np = snapshot.np_module
    _Image = snapshot.image_module
    _mp = snapshot.mp_module
    _dlib = snapshot.dlib_module
    _MTCNN = snapshot.mtcnn_class

    CV2_AVAILABLE = snapshot.cv2_available
    MEDIAPIPE_AVAILABLE = snapshot.mediapipe_available
    DLIB_AVAILABLE = snapshot.dlib_available
    MTCNN_AVAILABLE = snapshot.mtcnn_available
    _MTCNN_IMPORT_ERROR = snapshot.mtcnn_import_error
    _MEDIAPIPE_IMPORT_ERROR = snapshot.mediapipe_import_error
    _MEDIAPIPE_DRAWING_DISABLED = snapshot.mediapipe_drawing_disabled

    # Compatibility aliases used in legacy call-sites.
    cv2 = _cv2
    np = _np
    Image = _Image
    MTCNN = _MTCNN


def _ensure_dependencies() -> None:
    """Initialize runtime dependencies and sync compatibility aliases."""
    ensure_runtime_dependencies(logger)
    _sync_runtime_dependency_snapshot()


def _resolve_haar_cascade_dir() -> Path | None:
    return resolve_haar_cascade_dir(cv2_available=CV2_AVAILABLE, cv2_module=_cv2)


class QualityAnalyzer:
    """Quality analyzer using MediaPipe Face Mesh and staged fallbacks."""

    def __init__(
        self,
        use_face_mesh: bool = True,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        logger.info("[INIT] QualityAnalyzer.__init__ started")
        _ensure_dependencies()

        try:
            requested_stage = int(os.environ.get("PHOTOCLEANER_EYE_DETECTION_STAGE", "1"))
        except (ValueError, TypeError):
            logger.debug("Invalid EYE_DETECTION_STAGE value, using default", exc_info=True)
            requested_stage = 1

        self._eye_detection_stage = self._determine_available_stage(requested_stage)
        if self._eye_detection_stage != requested_stage:
            logger.info(
                "Eye Detection: Stufe %s angefordert, aber nur Stufe %s verfuegbar (fehlende Dependencies).",
                requested_stage,
                self._eye_detection_stage,
            )

        self.use_face_mesh = use_face_mesh and MEDIAPIPE_AVAILABLE
        self._face_mesh_warning_logged = False
        self.face_mesh = None
        self._base_options = None

        # Haar cascades are managed inside FaceDetector.
        self.face_cascade = None
        self.eye_cascade = None

        # Sync runtime dependency state into face_detector module.
        face_detector_module.CV2_AVAILABLE = CV2_AVAILABLE
        face_detector_module.MEDIAPIPE_AVAILABLE = MEDIAPIPE_AVAILABLE
        face_detector_module.DLIB_AVAILABLE = DLIB_AVAILABLE
        face_detector_module.MTCNN_AVAILABLE = MTCNN_AVAILABLE
        face_detector_module.cv2 = _cv2
        face_detector_module.np = _np
        face_detector_module.MTCNN = _MTCNN
        face_detector_module._dlib = _dlib
        face_detector_module._mp = _mp

        self.face_detector = FaceDetector(
            eye_detection_stage=self._eye_detection_stage,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.quality_scorer = QualityScorer(np_module=_np, cv2_module=_cv2)
        self.exif_extractor = ExifExtractor(image_module=_Image, cv2_module=_cv2)

        self._mtcnn_detector_cache = None
        self._mtcnn_lock = threading.Lock()
        self._mtcnn_infer_lock = threading.Lock()

        if MTCNN_AVAILABLE:
            logger.info("MTCNN: Available and ready (using TensorFlow backend)")
        elif _MTCNN_IMPORT_ERROR:
            if (
                "Disabled via PHOTOCLEANER_FACE_DETECTOR" in _MTCNN_IMPORT_ERROR
                or "Skipped by PHOTOCLEANER_SKIP_HEAVY_DEPS" in _MTCNN_IMPORT_ERROR
            ):
                logger.info("MTCNN: %s", _MTCNN_IMPORT_ERROR)
            else:
                logger.warning("MTCNN: Import failed - %s", _MTCNN_IMPORT_ERROR)
        else:
            logger.warning("MTCNN: Not available (unknown reason)")

        if not MEDIAPIPE_AVAILABLE:
            if use_face_mesh and _MEDIAPIPE_IMPORT_ERROR:
                logger.warning(
                    "MediaPipe import failed but was requested for face mesh analysis: %s",
                    _MEDIAPIPE_IMPORT_ERROR,
                )
            self.use_face_mesh = False

        if not CV2_AVAILABLE:
            if use_face_mesh:
                logger.warning("OpenCV not available but was requested - Face Mesh analysis disabled")
            self.use_face_mesh = False

        logger.info("[INIT] QualityAnalyzer.__init__ complete")

    def warmup(self) -> None:
        """Preload heavy models to avoid first-image delay."""
        global _MTCNN_WARNING_LOGGED

        logger.debug("[WARMUP] Starting model warmup...")

        try:
            if self.use_face_mesh:
                _ = self.face_detector._get_face_mesh_model()
        except (ImportError, RuntimeError, AttributeError) as error:
            logger.warning("Face Mesh warmup failed: %s", error, exc_info=True)

        try:
            if MTCNN_AVAILABLE and self._mtcnn_detector_cache is None and _MTCNN is not None:
                logger.info("[WARMUP] MTCNN: Preloading detector (this may take 10-30 seconds)...")
                import time

                start = time.time()
                self._mtcnn_detector_cache = _MTCNN()
                elapsed = time.time() - start
                logger.info("[WARMUP] MTCNN detector loaded in %.1fs", elapsed)
            elif MTCNN_AVAILABLE:
                logger.debug("[WARMUP] MTCNN already loaded")
            else:
                logger.debug("[WARMUP] MTCNN not available, skipping")
        except (ImportError, RuntimeError, AttributeError, OSError, Exception) as error:
            mark_mtcnn_unavailable(f"Warmup failed: {error}")
            _sync_runtime_dependency_snapshot()
            _MTCNN_WARNING_LOGGED = True
            logger.warning(
                "[WARMUP] MTCNN warmup failed (%s): %s. Falling back to Haar Cascade.",
                type(error).__name__,
                error,
            )

    def _determine_available_stage(self, requested_stage: int) -> int:
        return determine_available_eye_stage(
            requested_stage,
            cv2_available=CV2_AVAILABLE,
            dlib_available=DLIB_AVAILABLE,
            mediapipe_available=MEDIAPIPE_AVAILABLE,
            logger=logger,
        )

    def get_actual_stage(self) -> int:
        """Get active eye detection stage after graceful fallback."""
        return self._eye_detection_stage

    def get_stage_info(self) -> dict:
        """Get detailed stage/capability info for UI and diagnostics."""
        face_detector = os.environ.get("PHOTOCLEANER_FACE_DETECTOR", "mtcnn").lower()
        return build_stage_info(
            current_stage=self._eye_detection_stage,
            cv2_available=CV2_AVAILABLE,
            dlib_available=DLIB_AVAILABLE,
            mediapipe_available=MEDIAPIPE_AVAILABLE,
            mtcnn_available=MTCNN_AVAILABLE,
            face_detector=face_detector,
        )

    def __del__(self) -> None:
        self._cleanup_models()

    def _cleanup_models(self) -> None:
        """Close/clear heavy model resources to prevent memory growth."""
        if hasattr(self, "_mtcnn_detector_cache") and self._mtcnn_detector_cache:
            try:
                self._mtcnn_detector_cache = None
            except Exception as error:
                logger.debug("Error cleaning MTCNN: %s", error)

        if hasattr(self, "face_mesh") and self.face_mesh:
            try:
                if hasattr(self.face_mesh, "close"):
                    self.face_mesh.close()
                self.face_mesh = None
            except Exception as error:
                logger.debug("Error closing legacy face_mesh: %s", error)

    def _get_exif_orientation_from_pil(self, pil_image, image_path: Path) -> int:
        return self.exif_extractor.get_exif_orientation_from_pil(pil_image, image_path)

    def _extract_exif_data_from_pil(self, pil_image, image_path: Path) -> dict:
        return self.exif_extractor.extract_exif_data_from_pil(pil_image, image_path)

    def _extract_exif_data(self, image_path: Path) -> dict:
        return self.exif_extractor.extract_exif_data(image_path)

    def _rotate_image_from_exif(self, img: NDArray, orientation: int) -> NDArray:
        return self.exif_extractor.rotate_image_from_exif(img, orientation)

    def analyze_image(self, image_path: Path) -> QualityResult:
        """Analyze a single image for quality metrics."""
        _ensure_dependencies()

        try:
            if not CV2_AVAILABLE:
                return QualityResult(path=image_path, error="OpenCV not available")

            prepared = prepare_image_for_quality_analysis(
                image_path,
                cv2_module=_cv2,
                np_module=_np,
                image_module=_Image,
                mtcnn_available=MTCNN_AVAILABLE,
                mtcnn_detector_cache=self._mtcnn_detector_cache,
                max_analysis_dimension=2000,
                logger=logger,
            )
            if prepared is None:
                return QualityResult(path=image_path, error="Failed to load image")

            metadata = enrich_image_with_metadata(
                image_path,
                img=prepared.img,
                pil_img=prepared.pil_img,
                original_width=prepared.original_width,
                original_height=prepared.original_height,
                exif_extractor=self.exif_extractor,
                logger=logger,
            )

            execution = execute_quality_analysis(
                img=metadata.img,
                width=metadata.width,
                height=metadata.height,
                resolution_score=metadata.resolution_score,
                cv2_module=_cv2,
                quality_scorer=self.quality_scorer,
                face_detector=self.face_detector,
                image_name=image_path.name,
                logger=logger,
            )

            return QualityResult(
                path=image_path,
                face_quality=execution.face_quality,
                overall_sharpness=execution.overall_sharpness,
                lighting_score=execution.lighting_score,
                resolution_score=metadata.resolution_score,
                width=metadata.width,
                height=metadata.height,
                total_score=execution.total_score,
                camera_model=metadata.camera_model,
                exif_data=metadata.exif_data,
                iso_value=metadata.iso_value,
                aperture_value=metadata.aperture_value,
                focal_length=metadata.focal_length,
                exposure_time=metadata.exposure_time,
            )
        except Exception as error:
            logger.warning("Failed to analyze %s: %s", image_path, error)
            return QualityResult(path=image_path, error=str(error))

    def analyze_batch(
        self,
        image_paths: list[Path],
        progress_callback: Optional[callable] = None,
        max_workers: int = 4,
    ) -> list[QualityResult]:
        """Analyze multiple images in parallel and preserve input ordering."""
        logger.info("=== QualityAnalyzer.analyze_batch() STARTED ===")
        logger.info("Analyzing %s images with %s workers", len(image_paths), max_workers)

        results = run_quality_batch(
            image_paths=image_paths,
            analyze_image=self.analyze_image,
            progress_callback=progress_callback,
            max_workers=max_workers,
            logger=logger,
            error_result_factory=lambda path, error: QualityResult(path=path, error=str(error)),
        )

        logger.info("=== QualityAnalyzer.analyze_batch() COMPLETED ===")
        logger.info(
            "Analyzed %s images, %s successful",
            len(results),
            sum(1 for result in results if result.error is None),
        )
        return results
