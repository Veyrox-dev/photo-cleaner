"""
Scoring Constants for PhotoCleaner Pipeline

BUG-M1 FIX: Centralized constants for all scoring parameters.
Eliminates magic numbers and provides single source of truth for calibration.

This module defines all numerical constants used in image quality scoring,
making it easy to tune and maintain consistent behavior across the pipeline.
"""


class ScoringConstants:
    """Centralized scoring constants for quality analysis and auto-selection.
    
    BUG-M1 FIX: All magic numbers extracted to this class for maintainability.
    """
    
    # ==================== SHARPNESS SCORING ====================
    
    # Base sharpness divisor for 8MP photos
    SHARPNESS_BASE_DIVISOR = 5.0
    
    # Reference resolution for sharpness normalization (8MP baseline)
    SHARPNESS_REFERENCE_RESOLUTION_MP = 8.0
    
    # Reference face area for face sharpness normalization (500x500 = 250k pixels)
    SHARPNESS_REFERENCE_FACE_AREA = 250_000
    
    # Typical Laplacian variance ranges by resolution
    LAPLACIAN_VARIANCE_5MP = 350.0    # Lower detail density
    LAPLACIAN_VARIANCE_8MP = 500.0    # Baseline
    LAPLACIAN_VARIANCE_12MP = 650.0   # Higher detail density
    LAPLACIAN_VARIANCE_48MP = 1200.0  # Very high detail
    
    
    # ==================== SCORING WEIGHTS ====================
    
    # Component weights for final score (must sum to 1.0)
    WEIGHT_SHARPNESS = 0.20      # 20% - Image sharpness (Laplacian variance)
    WEIGHT_LIGHTING = 0.15       # 15% - Exposure quality
    WEIGHT_RESOLUTION = 0.10     # 10% - Megapixels
    WEIGHT_FACE_QUALITY = 0.55   # 55% - DOMINANT: Eyes open/face detection
    WEIGHT_RECENCY = 0.00        # 0% - Reserved for future group-context scoring
    
    @classmethod
    def get_weights(cls) -> list[float]:
        """Get scoring weights as list in order: [sharpness, lighting, resolution, face, recency]."""
        return [
            cls.WEIGHT_SHARPNESS,
            cls.WEIGHT_LIGHTING,
            cls.WEIGHT_RESOLUTION,
            cls.WEIGHT_FACE_QUALITY,
            cls.WEIGHT_RECENCY,
        ]
    
    
    # ==================== EYE DETECTION THRESHOLDS ====================
    
    # Eye Aspect Ratio (EAR) thresholds for different detection methods
    EAR_THRESHOLD_MEDIAPIPE = 0.015  # MediaPipe Face Mesh (Stage 3)
    EAR_THRESHOLD_DLIB = 0.2         # dlib 68-point landmarks (Stage 2)
    
    # Haar Cascade minimum eye detection count
    HAAR_MIN_EYES_FOR_OPEN = 2       # Need 2+ eyes detected for "open" status
    
    
    # ==================== ISO-AWARE SCORING ====================
    
    # ISO thresholds for low-light tolerance adjustments
    ISO_THRESHOLD_MEDIUM = 800       # Medium-high ISO
    ISO_THRESHOLD_HIGH = 1600        # High ISO (significant noise)
    ISO_THRESHOLD_VERY_HIGH = 3200   # Very high ISO (heavy noise)
    
    # Sharpness tolerance factors for high-ISO images
    # Lower factor = more lenient (divisor gets larger, score threshold relaxed)
    ISO_TOLERANCE_MEDIUM = 0.9       # 10% more lenient at ISO 800-1599
    ISO_TOLERANCE_HIGH = 0.75        # 25% more lenient at ISO 1600-3199
    ISO_TOLERANCE_VERY_HIGH = 0.6    # 40% more lenient at ISO 3200+
    
    
    # ==================== RESOLUTION SCORING ====================
    
    # Resolution baseline for modern smartphones (2020+)
    RESOLUTION_BASELINE_MODERN = 12.0    # 12MP standard
    RESOLUTION_BASELINE_LEGACY = 5.0     # 5MP for older devices
    RESOLUTION_BASELINE_VINTAGE = 2.0    # 2MP for very old cameras
    
    # Minimum realistic resolution to filter garbage data
    RESOLUTION_MIN_REALISTIC_MP = 0.1    # At least 0.1MP (e.g., 320x320)
    
    
    # ==================== LIGHTING/EXPOSURE SCORING ====================
    
    # Ideal brightness range for histogram analysis
    LIGHTING_IDEAL_BRIGHTNESS_MIN = 110
    LIGHTING_IDEAL_BRIGHTNESS_MAX = 140
    LIGHTING_IDEAL_BRIGHTNESS_CENTER = 125
    
    # Good contrast threshold (standard deviation)
    LIGHTING_GOOD_CONTRAST = 40.0
    LIGHTING_CONTRAST_REFERENCE = 50.0
    
    # Clipping thresholds (over/underexposure detection)
    LIGHTING_DARK_PIXEL_THRESHOLD = 20    # Pixels below this = underexposed
    LIGHTING_BRIGHT_PIXEL_THRESHOLD = 235  # Pixels above this = overexposed
    
    
    # ==================== EXIF VALIDATION RANGES ====================
    
    # Realistic sensor value ranges for boundary validation (BUG-C6 related)
    
    # ISO range: 1 to 409600 (high-end cameras like Sony A7S III)
    ISO_MIN = 1
    ISO_MAX = 409600
    
    # Aperture range: f/0.95 to f/64 (realistic physical limits)
    APERTURE_MIN = 0.5
    APERTURE_MAX = 100.0
    
    # Focal length range: 1mm (fisheye) to 5000mm (extreme telephoto)
    FOCAL_LENGTH_MIN = 0.0
    FOCAL_LENGTH_MAX = 5000.0
    
    # Exposure time range: 1/8000s to 60s
    EXPOSURE_TIME_MIN = 0.0001  # 1/10000s
    EXPOSURE_TIME_MAX = 60.0    # 60 seconds
    
    
    # ==================== FACE DETECTION ====================
    
    # Gaze and head straightness thresholds (MediaPipe)
    GAZE_CENTER_TOLERANCE = 0.03  # Iris center deviation tolerance
    HEAD_TILT_ANGLE_TOLERANCE = 0.05  # Nose/face angle tolerance
    
    # Face quality scoring
    FACE_QUALITY_BASE_SCORE = 70.0       # Base score for face with eyes open
    FACE_QUALITY_CONFIDENCE_BOOST = 30.0  # Max boost from confidence (0.0-1.0)
    FACE_QUALITY_CLOSED_EYES_MALUS = 20.0  # Score when eyes closed
    FACE_QUALITY_NO_FACE_NEUTRAL = 60.0    # Neutral score when no face

    # Eye openness scoring (MediaPipe EAR-based)
    EAR_SCORE_MIN = 0.005   # Very closed eyes
    EAR_SCORE_MAX = 0.040   # Wide open eyes

    # Gaze scoring (normalized deviation from eye center)
    GAZE_MAX_DEVIATION = 0.08

    # Head pose scoring (normalized deviation from straight)
    HEAD_TILT_MAX_DEVIATION = 0.15

    # Smile scoring (mouth width/height ratio)
    SMILE_RATIO_MIN = 1.6
    SMILE_RATIO_MAX = 3.0

    # Face sharpness normalization
    FACE_SHARPNESS_REFERENCE = 500.0

    # Face quality weighting (sum ~1.0)
    FACE_SCORE_WEIGHT_EYES = 0.40
    FACE_SCORE_WEIGHT_SHARPNESS = 0.25
    FACE_SCORE_WEIGHT_GAZE = 0.15
    FACE_SCORE_WEIGHT_HEAD_POSE = 0.10
    FACE_SCORE_WEIGHT_SMILE = 0.10
    
    
    # ==================== MEDIAPIPE CONFIGURATION ====================
    
    # Timeout for MediaPipe Face Mesh processing (BUG-C5 related)
    MEDIAPIPE_TIMEOUT_SECONDS = 10.0
    
    # Max number of faces to detect
    MEDIAPIPE_MAX_FACES = 5
    
    # Detection confidence thresholds
    MEDIAPIPE_MIN_DETECTION_CONFIDENCE = 0.5
    MEDIAPIPE_MIN_TRACKING_CONFIDENCE = 0.5
    
    
    # ==================== CACHE AND PERFORMANCE ====================
    
    # Batch progress reporting interval
    BATCH_PROGRESS_REPORT_INTERVAL = 10  # Log every N images
    
    # Config change detection (cache invalidation trigger)
    CONFIG_HASH_CHECK_ENABLED = True
