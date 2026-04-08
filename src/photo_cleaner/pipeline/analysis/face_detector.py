"""
Face Detection Module - MTCNN + Haar Cascade + MediaPipe strategies

Detects faces and analyzes eye status using multiple strategies:
- MTCNN: Modern, accurate face detection (default)
- Haar Cascade: Legacy fallback detector
- dlib: Optional escalation for harder cases
- MediaPipe: Optional eye coordinate analysis

All detectors return multi-person eye analysis with quality scores.
"""
import logging
import os
import threading
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray
else:
    NDArray = object

from photo_cleaner.config import AppConfig
from photo_cleaner.pipeline.analysis.face_mesh_resolver import resolve_face_mesh_ctor
from photo_cleaner.pipeline.analysis.haar_cascade_resolver import resolve_haar_cascade_dir
from photo_cleaner.pipeline.scoring_constants import ScoringConstants
from photo_cleaner.pipeline.analysis.models import FaceQuality, PersonEyeStatus

logger = logging.getLogger(__name__)

# Will be set by _ensure_dependencies in quality_analyzer
CV2_AVAILABLE = True
MEDIAPIPE_AVAILABLE = True
DLIB_AVAILABLE = True
MTCNN_AVAILABLE = True

# Global variables (set by quality_analyzer._ensure_dependencies)
cv2 = None
np = None
MTCNN = None
_dlib = None
_mp = None

# Logging flags
_MTCNN_WARNING_LOGGED = False
_FACE_MESH_WARNING_LOGGED = False


class FaceDetector:
    """Encapsulates face detection logic with multi-strategy support."""
    
    def __init__(self, eye_detection_stage: int = 1, min_tracking_confidence: float = 0.5):
        """Initialize face detector with configuration.
        
        Args:
            eye_detection_stage: Detection pipeline stage (0=none, 1=haar/mtcnn, 2=dlib, 3=mediapipe)
            min_tracking_confidence: MediaPipe minimum tracking confidence threshold
        """
        self._eye_detection_stage = eye_detection_stage
        self._min_tracking_confidence = min_tracking_confidence
        
        # State caches
        self._face_cascade = None
        self._eye_cascade = None
        self._face_mesh_cache = None
        self._mtcnn_detector_cache = None
        
        # Thread safety
        self._mtcnn_lock = threading.Lock()
        self._mtcnn_infer_lock = threading.Lock()
        
        # Configuration tracking
        self._last_config = None
        self.use_face_mesh = True
        self._face_mesh_warning_logged = False
        
        # Load cascades if available
        self._load_cascades()
    
    def _load_cascades(self):
        """Load Haar cascade classifiers using shared resolver."""
        if not CV2_AVAILABLE or cv2 is None:
            logger.debug("OpenCV not available, Haar cascades disabled")
            return
        
        try:
            cascade_dir = resolve_haar_cascade_dir(cv2_available=CV2_AVAILABLE, cv2_module=cv2)
            if cascade_dir is None:
                return

            face_cascade_path = Path(cascade_dir) / "haarcascade_frontalface_default.xml"
            eye_cascade_path = Path(cascade_dir) / "haarcascade_eye_tree_eyeglasses.xml"
            if not eye_cascade_path.exists():
                eye_cascade_path = Path(cascade_dir) / "haarcascade_eye.xml"
            
            if face_cascade_path.exists():
                self._face_cascade = cv2.CascadeClassifier(str(face_cascade_path))
            if eye_cascade_path.exists():
                self._eye_cascade = cv2.CascadeClassifier(str(eye_cascade_path))
            
            logger.debug("Haar cascades loaded successfully")
        except Exception as e:
            logger.debug(f"Failed to load Haar cascades: {e}")
    
    @property
    def face_cascade(self):
        """Get face cascade, loading if needed."""
        if self._face_cascade is None:
            self._load_cascades()
        return self._face_cascade
    
    @property
    def eye_cascade(self):
        """Get eye cascade, loading if needed."""
        if self._eye_cascade is None:
            self._load_cascades()
        return self._eye_cascade
    
    def _check_config_changed(self) -> bool:
        """Check if configuration has changed since last check."""
        current_config = (
            AppConfig.get_config_hash() if hasattr(AppConfig, 'get_config_hash') else None
        )
        if self._last_config != current_config:
            self._last_config = current_config
            return True
        return False
    
    def _invalidate_face_mesh_cache(self):
        """Invalidate cached face mesh model on config change."""
        if self._face_mesh_cache is not None:
            try:
                self._face_mesh_cache.close()
            except (AttributeError, RuntimeError):
                pass
            self._face_mesh_cache = None
            logger.debug("Face mesh cache invalidated due to config change")
    
    def _get_face_mesh_model(self):
        """Get cached MediaPipe Face Mesh model (singleton pattern).
        
        FEATURE: Includes config-change invalidation hook.
        Loads model on first use, then reuses same instance for all images.
        This gives 10-100x speedup vs creating new instance per image.
        
        Returns:
            mp.solutions.face_mesh.FaceMesh instance or None
        """
        # Check for config changes and invalidate cache if needed
        if self._check_config_changed():
            self._invalidate_face_mesh_cache()
        
        if not MEDIAPIPE_AVAILABLE or not self.use_face_mesh or _mp is None:
            return None
        
        # Lazy-load on first use
        if self._face_mesh_cache is None:
            try:
                face_mesh_ctor = resolve_face_mesh_ctor(
                    mediapipe_available=MEDIAPIPE_AVAILABLE,
                    mp_module=_mp,
                )
                if face_mesh_ctor is None:
                    self.use_face_mesh = False
                    return None
                
                self._face_mesh_cache = face_mesh_ctor(
                    static_image_mode=True,
                    max_num_faces=10,
                    refine_landmarks=True,
                    min_detection_confidence=0.7,
                    min_tracking_confidence=self._min_tracking_confidence,
                )
                logger.debug("MediaPipe Face Mesh model loaded and cached (min_detection_confidence=0.7)")
            except (ImportError, RuntimeError, AttributeError, ValueError) as e:
                logger.warning(f"Failed to load MediaPipe Face Mesh: {e}", exc_info=True)
                self.use_face_mesh = False
                return None
        
        return self._face_mesh_cache
    
    def analyze_faces(self, img: NDArray) -> FaceQuality:
        """Detect faces using progressive strategy (main entry point).
        
        Stages:
        - Stage 0: No dependencies → return no face
        - Stage 1: MTCNN (modern) OR Haar Cascade (legacy fallback)
        - Stage 2: dlib 68-point landmarks (optional escalation)
        - Stage 3: MediaPipe standalone (optional)
        """
        return self._analyze_faces_progressive(img)
    
    def _analyze_faces_progressive(self, img: NDArray) -> FaceQuality:
        """Run progressive eye detection across stages based on configuration."""
        if self._eye_detection_stage == 0:
            logger.debug("No detection stage configured, returning no face")
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
                global _MTCNN_WARNING_LOGGED
                if not _MTCNN_WARNING_LOGGED:
                    logger.warning("MTCNN requested but not available, falling back to Haar Cascade")
                    _MTCNN_WARNING_LOGGED = True
            logger.debug("Using Haar Cascade for face detection (legacy)")
            result = self._analyze_faces_haar(img)
        
        if self._eye_detection_stage <= 1:
            return result
        
        # Escalate if uncertain or failed (and Stage 2 is available)
        need_escalate = (not result.has_face) or (not result.all_eyes_open)
        if self._eye_detection_stage >= 2 and need_escalate:
            if not DLIB_AVAILABLE:
                logger.debug("Stage 2 configured, but dlib not available")
                return result
            
            logger.debug("Escalating to dlib (Stage 2) for improved eye detection...")
            dl = self._analyze_faces_dlib(img)
            if dl.has_face and dl.all_eyes_open:
                return dl
            if dl.has_face:
                result = dl
        
        # Escalate to Stage 3 if needed (and available)
        if self._eye_detection_stage >= 3 and ((not result.has_face) or (not result.all_eyes_open)):
            if not MEDIAPIPE_AVAILABLE:
                logger.warning("Stage 3 configured, but MediaPipe not available")
                return result
            
            logger.debug("Escalating to MediaPipe Face Mesh (Stage 3) for maximal accuracy...")
            mpres = self._analyze_faces_mediapipe(img)
            if mpres.has_face:
                return mpres
        
        return result
    
    def _analyze_faces_haar(self, img: NDArray) -> FaceQuality:
        """Stage 1: Face + eye detection via Haar cascades (cached for performance)."""
        try:
            if not self.face_cascade or not self.eye_cascade:
                logger.debug("Face/Eye cascades not loaded")
                return FaceQuality(has_face=False)
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect ALL faces
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
            )
            
            # Filter false positives
            MIN_FACE_SIZE = 350
            filtered_faces = [(x, y, w, h) for (x, y, w, h) in faces if w >= MIN_FACE_SIZE and h >= MIN_FACE_SIZE]
            
            if len(filtered_faces) < len(faces):
                logger.debug(f"Filtered {len(faces) - len(filtered_faces)} false positive faces (too small)")
            
            logger.debug(f"Face detection: {len(filtered_faces)} faces found")
            
            if len(filtered_faces) == 0:
                return FaceQuality(has_face=False)
            
            faces = sorted(filtered_faces, key=lambda f: f[2] * f[3], reverse=True)
            
            person_statuses = []
            all_eyes_open = True
            largest_person_status = None
            
            for person_id, (x, y, w, h) in enumerate(faces):
                face_region = img[y:y+h, x:x+w]
                gray_face = gray[y:y+h, x:x+w]
                face_size = w * h
                
                logger.debug(f"  Person {person_id+1}: {w}×{h} pixels")
                
                eyes = self.eye_cascade.detectMultiScale(
                    gray_face, scaleFactor=1.1, minNeighbors=4, minSize=(15, 15)
                )
                
                eyes_open = len(eyes) >= 2
                
                logger.debug(f"     Eyes found: {len(eyes)} → {'OPEN ✅' if eyes_open else 'CLOSED ❌'}")
                
                if not eyes_open:
                    all_eyes_open = False
                    logger.debug(f"⚠️  Person {person_id+1}: eyes closed → image disqualified")
                
                # Face sharpness
                laplacian = cv2.Laplacian(gray_face, cv2.CV_64F)
                variance = laplacian.var()
                region_area = face_region.shape[0] * face_region.shape[1]
                reference_area = 250_000
                normalization_factor = np.sqrt(region_area / reference_area)
                face_sharpness = variance * normalization_factor
                
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
                
                if person_id == 0:
                    largest_person_status = person_status
                
                # Early exit on hard rule violation
                if not eyes_open and not AppConfig.is_debug():
                    logger.info(f"Hard Rule: Person {person_id+1} has closed eyes - early exit")
                    break
            
            logger.info(f"Analysis complete: {len(faces)} persons, all eyes open: {all_eyes_open}")
            
            best_person = self._select_best_person(person_statuses) or largest_person_status
            best_face_sharpness = best_person.face_sharpness if best_person else 0.0
            best_eyes_open = best_person.eyes_open if best_person else False
            
            return FaceQuality(
                has_face=True,
                eyes_open=best_eyes_open,
                all_eyes_open=all_eyes_open,
                gaze_forward=True,
                head_straight=True,
                face_sharpness=best_face_sharpness,
                confidence=0.65,
                num_faces=len(faces),
                eye_count=sum(1 for p in person_statuses if p.eyes_open) * 2,
                face_count=len(faces),
                person_eye_statuses=person_statuses,
                best_person_id=best_person.person_id if best_person else 0,
                eye_open_score=best_person.eyes_open_score if best_person else None,
                gaze_forward_score=best_person.gaze_score if best_person else None,
                head_pose_score=best_person.head_pose_score if best_person else None,
                smile_score=best_person.smile_score if best_person else None,
            )
        
        except Exception as e:
            logger.debug(f"Haar face analysis failed: {e}")
            return FaceQuality(has_face=False)
    
    def _analyze_faces_mtcnn(self, img: NDArray) -> FaceQuality:
        """MTCNN + MediaPipe two-stage face detection."""
        global _MTCNN_WARNING_LOGGED, MTCNN_AVAILABLE
        
        try:
            if not MTCNN_AVAILABLE:
                if not _MTCNN_WARNING_LOGGED:
                    logger.debug("MTCNN not available, falling back to Haar Cascade")
                    _MTCNN_WARNING_LOGGED = True
                return self._analyze_faces_haar(img)
            
            height, width = img.shape[:2]
            
            # Optimization: Downscale image (max 1600px edge)
            MAX_EDGE = 1600
            scale_factor = 1.0
            if max(height, width) > MAX_EDGE:
                scale_factor = MAX_EDGE / max(height, width)
                new_height = int(height * scale_factor)
                new_width = int(width * scale_factor)
                img_scaled = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logger.debug(f"MTCNN: Scaled from {width}×{height} to {new_width}×{new_height}")
            else:
                img_scaled = img
                logger.debug(f"MTCNN: Image already small ({width}×{height})")
            
            rgb = cv2.cvtColor(img_scaled, cv2.COLOR_BGR2RGB)
            
            # Stage 1: MTCNN detection
            if self._mtcnn_detector_cache is None:
                with self._mtcnn_lock:
                    if self._mtcnn_detector_cache is None:
                        try:
                            logger.debug("MTCNN: Loading detector (first use)")
                            self._mtcnn_detector_cache = MTCNN()
                        except Exception as e:
                            MTCNN_AVAILABLE = False
                            self._mtcnn_detector_cache = None
                            _MTCNN_WARNING_LOGGED = False
                            logger.error(f"MTCNN initialization failed: {e}. Falling back to Haar.")
                            return None
            
            detector = self._mtcnn_detector_cache
            
            with self._mtcnn_infer_lock:
                try:
                    detections = detector.detect_faces(rgb)
                except Exception as exc:
                    logger.error(f"MTCNN detect_faces failed: {exc}", exc_info=True)
                    # Retry once
                    try:
                        self._mtcnn_detector_cache = MTCNN()
                        detector = self._mtcnn_detector_cache
                    except Exception as reinit_exc:
                        logger.error(f"MTCNN reinit failed: {reinit_exc}", exc_info=True)
                        raise
                    detections = detector.detect_faces(rgb)
            
            if not detections:
                logger.debug("MTCNN: No faces detected")
                return FaceQuality(has_face=False)
            
            # Filter by confidence
            MIN_CONFIDENCE = 0.90
            filtered_detections = [d for d in detections if d['confidence'] >= MIN_CONFIDENCE]
            
            if not filtered_detections:
                logger.debug(f"MTCNN: All faces filtered (confidence < {MIN_CONFIDENCE})")
                return FaceQuality(has_face=False)
            
            logger.debug(f"MTCNN: {len(filtered_detections)} faces detected")
            
            # Scale bounding boxes back to original coordinates
            if scale_factor < 1.0:
                for d in filtered_detections:
                    x, y, w, h = d['box']
                    d['box'] = (int(x / scale_factor), int(y / scale_factor), int(w / scale_factor), int(h / scale_factor))
            
            filtered_detections.sort(key=lambda d: d['box'][2] * d['box'][3], reverse=True)
            
            # Stage 2: MediaPipe eye analysis on MTCNN faces
            person_statuses = []
            all_eyes_open = True
            largest_person_status = None
            
            face_mesh = self._get_face_mesh_model()
            if face_mesh is None:
                # Fallback: MTCNN-only detection
                if not self._face_mesh_warning_logged:
                    logger.warning("MediaPipe not available, using MTCNN-only detection")
                    self._face_mesh_warning_logged = True
                for pid, detection in enumerate(filtered_detections):
                    x, y, w, h = detection['box']
                    ps = PersonEyeStatus(
                        person_id=pid + 1,
                        eyes_open=True,
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
                    all_eyes_open=True,
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
            
            # MediaPipe available - analyze each MTCNN face
            for pid, detection in enumerate(filtered_detections):
                x, y, w, h = detection['box']
                
                x = max(0, x)
                y = max(0, y)
                x2 = min(width, x + w)
                y2 = min(height, y + h)
                
                # Extract face region with padding
                padding = int(max(w, h) * 0.2)
                x1_pad = max(0, x - padding)
                y1_pad = max(0, y - padding)
                x2_pad = min(width, x2 + padding)
                y2_pad = min(height, y2 + padding)
                
                face_region = img[y1_pad:y2_pad, x1_pad:x2_pad]
                
                if face_region.size == 0:
                    logger.debug(f"Person {pid+1}: Empty face region, skipping")
                    continue
                
                face_rgb = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)
                
                try:
                    result = face_mesh.process(face_rgb)
                    
                    if result.multi_face_landmarks and len(result.multi_face_landmarks) > 0:
                        landmarks = result.multi_face_landmarks[0].landmark
                        
                        eyes_open = self._check_eyes_open(landmarks)
                        face_sharpness = self._calculate_face_sharpness(
                            face_region, landmarks,
                            face_region.shape[1], face_region.shape[0]
                        )
                        
                        eyes_open_score = self._calculate_eye_openness_score(landmarks)
                        gaze_score = self._calculate_gaze_score(landmarks)
                        head_pose_score = self._calculate_head_pose_score(landmarks)
                        smile_score = self._calculate_smile_score(landmarks)
                        
                        logger.debug(f"  Person {pid+1}: {w}×{h}px, confidence={detection['confidence']:.2f}, eyes={'OPEN ✅' if eyes_open else 'CLOSED ❌'}")
                        
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
                    else:
                        logger.debug(f"Person {pid+1}: No landmarks found, assuming eyes open")
                        ps = PersonEyeStatus(
                            person_id=pid + 1,
                            eyes_open=True,
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
                    ps = PersonEyeStatus(
                        person_id=pid + 1,
                        eyes_open=True,
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
            
            logger.info(f"MTCNN+MediaPipe: {len(person_statuses)} persons, all eyes open: {all_eyes_open}")
            
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
        """dlib 68-point facial landmarks detection."""
        try:
            if not DLIB_AVAILABLE or _dlib is None:
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
                """Eye Aspect Ratio for 6 points."""
                from math import dist
                A = dist(points[1], points[5])
                B = dist(points[2], points[4])
                C = dist(points[0], points[3])
                return (A + B) / (2.0 * C + 1e-6)
            
            for pid, rect in enumerate(rects):
                shape = predictor(gray, rect)
                coords = [(shape.part(i).x, shape.part(i).y) for i in range(68)]
                left = coords[36:42]
                right = coords[42:48]
                left_ear = _ear(left)
                right_ear = _ear(right)
                ear = (left_ear + right_ear) / 2.0
                eyes_open = ear > 0.2
                
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
        """MediaPipe Face Mesh detection with timeout protection."""
        try:
            if not MEDIAPIPE_AVAILABLE or _mp is None:
                logger.debug("MediaPipe not available")
                return FaceQuality(has_face=False)
            
            height, width = img.shape[:2]
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            face_mesh = self._get_face_mesh_model()
            if face_mesh is None:
                return FaceQuality(has_face=False)
            
            # Timeout protection
            import queue
            result_queue = queue.Queue()
            error_queue = queue.Queue()
            
            def run_face_mesh():
                try:
                    result = face_mesh.process(rgb)
                    result_queue.put(result)
                except Exception as e:
                    error_queue.put(e)
            
            mesh_thread = threading.Thread(target=run_face_mesh, daemon=True)
            mesh_thread.start()
            mesh_thread.join(timeout=10.0)
            
            if mesh_thread.is_alive():
                logger.warning("MediaPipe Face Mesh timeout after 10s - possible OOM")
                return FaceQuality(has_face=False)
            
            if not error_queue.empty():
                e = error_queue.get()
                raise e
            
            if result_queue.empty():
                return FaceQuality(has_face=False)
            
            res = result_queue.get()
            landmarks_list = res.multi_face_landmarks
            if not landmarks_list:
                return FaceQuality(has_face=False)
            
            # Filter false positives
            MIN_FACE_SIZE = 50
            filtered_landmarks = []
            
            for lm in landmarks_list:
                lm_pts = lm.landmark
                x_coords = [pt.x * width for pt in lm_pts]
                y_coords = [pt.y * height for pt in lm_pts]
                
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                face_width = x_max - x_min
                face_height = y_max - y_min
                
                if face_width >= MIN_FACE_SIZE and face_height >= MIN_FACE_SIZE:
                    filtered_landmarks.append(lm)
                else:
                    logger.debug(f"False positive filtered: {face_width:.0f}×{face_height:.0f}px (too small)")
            
            if not filtered_landmarks:
                logger.debug("All detected faces were false positives")
                return FaceQuality(has_face=False)
            
            logger.debug(f"Face detection: {len(filtered_landmarks)} faces found")
            
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
                    face_size_pixels=width*height,
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
    
    # Helper methods for facial landmark analysis
    
    def _check_eyes_open(self, landmarks) -> bool:
        """Check if eyes are open using Eye Aspect Ratio."""
        left_top = landmarks[159].y
        left_bottom = landmarks[145].y
        left_ear = abs(left_top - left_bottom)
        
        right_top = landmarks[386].y
        right_bottom = landmarks[374].y
        right_ear = abs(right_top - right_bottom)
        
        ear = (left_ear + right_ear) / 2
        return ear > ScoringConstants.EAR_THRESHOLD_MEDIAPIPE
    
    def _check_gaze_forward(self, landmarks) -> bool:
        """Check if gaze is forward."""
        left_iris = landmarks[468].x if len(landmarks) > 468 else landmarks[33].x
        left_inner = landmarks[133].x
        left_outer = landmarks[33].x
        
        right_iris = landmarks[473].x if len(landmarks) > 473 else landmarks[362].x
        right_inner = landmarks[362].x
        right_outer = landmarks[263].x
        
        left_centered = abs(left_iris - (left_inner + left_outer) / 2) < ScoringConstants.GAZE_CENTER_TOLERANCE
        right_centered = abs(right_iris - (right_inner + right_outer) / 2) < ScoringConstants.GAZE_CENTER_TOLERANCE
        
        return left_centered and right_centered
    
    def _check_head_straight(self, landmarks) -> bool:
        """Check if head is straight."""
        nose_top = landmarks[168]
        nose_bottom = landmarks[2]
        
        left_cheek = landmarks[234]
        right_cheek = landmarks[454]
        
        nose_angle = abs(nose_top.x - nose_bottom.x)
        face_tilt = abs(left_cheek.y - right_cheek.y)
        
        return nose_angle < ScoringConstants.HEAD_TILT_ANGLE_TOLERANCE and face_tilt < ScoringConstants.HEAD_TILT_ANGLE_TOLERANCE
    
    def _calculate_face_sharpness(self, img: NDArray, landmarks, width: int, height: int) -> float:
        """Calculate sharpness in face region."""
        x_coords = [lm.x * width for lm in landmarks]
        y_coords = [lm.y * height for lm in landmarks]
        
        x_min = max(0, int(min(x_coords)) - 20)
        x_max = min(width, int(max(x_coords)) + 20)
        y_min = max(0, int(min(y_coords)) - 20)
        y_max = min(height, int(max(y_coords)) + 20)
        
        face_region = img[y_min:y_max, x_min:x_max]
        
        if face_region.size == 0:
            return 0.0
        
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray_face, cv2.CV_64F)
        variance = laplacian.var()
        
        region_area = face_region.shape[0] * face_region.shape[1]
        reference_area = ScoringConstants.SHARPNESS_REFERENCE_FACE_AREA
        normalization_factor = np.sqrt(region_area / reference_area)
        
        sharpness = variance * normalization_factor
        return sharpness
    
    def _normalize_face_sharpness_score(self, face_sharpness: float) -> float:
        """Normalize face sharpness to 0-100 score."""
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
        """Return eye contact score (0-100)."""
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
        """Return head pose score (0-100)."""
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
        """Return smile score (0-100)."""
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
        """Select best person among multiple faces."""
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
