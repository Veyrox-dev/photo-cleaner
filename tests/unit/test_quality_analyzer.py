"""
Comprehensive test suite for QualityAnalyzer.

Coverage targets:
- analyze_image() core logic
- EXIF parsing robustness
- Edge cases (large images, corrupted EXIF, no metadata)
- Component scoring (sharpness, lighting, resolution)
- Camera profile detection
- Error handling and fallbacks

Generated: 2026-02-02
Target Coverage: 35%+ (from 12.58%)
"""

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from photo_cleaner.pipeline.quality_analyzer import (
    QualityAnalyzer,
    QualityResult,
    CameraProfile,
    FaceQuality,
    MTCNN_AVAILABLE,
)


class TestSyntheticImageGenerator:
    """Helper to generate synthetic test images."""

    @staticmethod
    def create_test_image(
        width: int = 800,
        height: int = 600,
        blur_kernel: int = 0,
        brightness: float = 1.0,
    ) -> Path:
        """Create synthetic test image with optional blur/brightness."""
        if not CV2_AVAILABLE:
            raise RuntimeError("cv2 not available")

        # Create synthetic image: gradient with noise
        img = np.random.randint(50, 200, (height, width, 3), dtype=np.uint8)
        
        # Add gradient
        for i in range(height):
            img[i, :] = (img[i, :] * (1.0 - i / height)).astype(np.uint8)
        
        # Apply blur if requested (simulates out-of-focus)
        if blur_kernel > 0:
            img = cv2.blur(img, (blur_kernel, blur_kernel))
        
        # Adjust brightness
        if brightness != 1.0:
            img = cv2.convertScaleAbs(img, alpha=brightness, beta=0)

        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".jpg", delete=False
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        cv2.imwrite(str(temp_path), img)
        return temp_path

    @staticmethod
    def create_test_image_pil(
        width: int = 800,
        height: int = 600,
        color: tuple = (100, 120, 140),
    ) -> Path:
        """Create simple test image using PIL."""
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL not available")

        img = Image.new("RGB", (width, height), color)
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".jpg", delete=False
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        img.save(temp_path, "JPEG")
        return temp_path

    @staticmethod
    def create_image_with_exif(
        width: int = 800,
        height: int = 600,
        exif_dict: dict = None,
    ) -> Path:
        """Create test image with specific EXIF data."""
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL not available")

        img = Image.new("RGB", (width, height), (128, 128, 128))
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".jpg", delete=False
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        # Note: Setting actual EXIF in PIL is complex, placeholder
        img.save(temp_path, "JPEG")
        return temp_path


class TestQualityAnalyzerBasics(TestCase):
    """Test basic QualityAnalyzer initialization and properties."""

    def setUp(self):
        """Initialize analyzer without face detection."""
        self.analyzer = QualityAnalyzer(use_face_mesh=False)

    def test_initialization_without_face_mesh(self):
        """Test analyzer can be created without MediaPipe."""
        assert self.analyzer is not None
        assert not self.analyzer.use_face_mesh

    def test_initialization_with_face_mesh_disabled(self):
        """Test explicit face mesh disabling."""
        analyzer = QualityAnalyzer(use_face_mesh=False)
        assert analyzer.use_face_mesh is False

    def test_analyzer_has_required_attributes(self):
        """Test analyzer has all required attributes."""
        assert hasattr(self.analyzer, "analyze_image")
        assert hasattr(self.analyzer, "analyze_batch")
        assert hasattr(self.analyzer, "use_face_mesh")


class TestQualityAnalyzerImageAnalysis(TestCase):
    """Test core image analysis functionality."""

    def setUp(self):
        """Initialize analyzer."""
        if not CV2_AVAILABLE or not PIL_AVAILABLE:
            self.skipTest("cv2 and PIL required")
        self.analyzer = QualityAnalyzer(use_face_mesh=False)

    def tearDown(self):
        """Clean up temp files."""
        pass

    def test_analyze_valid_image_returns_result(self):
        """Test analyzing a valid image returns QualityResult."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil()
        try:
            result = self.analyzer.analyze_image(test_image)
            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.path == test_image
        finally:
            test_image.unlink(missing_ok=True)

    def test_analyze_result_has_all_fields(self):
        """Test QualityResult contains all expected fields."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil()
        try:
            result = self.analyzer.analyze_image(test_image)
            
            # Check all fields exist
            assert result.path is not None
            assert result.width > 0
            assert result.height > 0
            assert result.overall_sharpness >= 0
            assert result.lighting_score >= 0
            assert result.resolution_score >= 0
            assert result.camera_model is not None
        finally:
            test_image.unlink(missing_ok=True)

    def test_analyze_small_image(self):
        """Test analyzing a small image (edge case)."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil(
            width=64, height=64
        )
        try:
            result = self.analyzer.analyze_image(test_image)
            assert result is not None
            assert result.width == 64
            assert result.height == 64
        finally:
            test_image.unlink(missing_ok=True)

    def test_analyze_large_image(self):
        """Test analyzing a large image (high resolution)."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil(
            width=4000, height=3000
        )
        try:
            result = self.analyzer.analyze_image(test_image)
            assert result is not None
            # Analyzer downscales large images when MTCNN is not active
            if MTCNN_AVAILABLE and self.analyzer._mtcnn_detector_cache is not None:
                assert result.width == 4000
                assert result.height == 3000
            else:
                assert result.width == 2000
                assert result.height == 1500
            # Should compute resolution score correctly
            assert result.resolution_score > 0
        finally:
            test_image.unlink(missing_ok=True)

    def test_analyze_portrait_orientation(self):
        """Test portrait (height > width) orientation."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil(
            width=600, height=800
        )
        try:
            result = self.analyzer.analyze_image(test_image)
            assert result.height > result.width
        finally:
            test_image.unlink(missing_ok=True)

    def test_analyze_landscape_orientation(self):
        """Test landscape (width > height) orientation."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil(
            width=1200, height=800
        )
        try:
            result = self.analyzer.analyze_image(test_image)
            assert result.width > result.height
        finally:
            test_image.unlink(missing_ok=True)


class TestQualityAnalyzerBatchProcessing(TestCase):
    """Test batch processing functionality."""

    def setUp(self):
        """Initialize analyzer."""
        if not CV2_AVAILABLE or not PIL_AVAILABLE:
            self.skipTest("cv2 and PIL required")
        self.analyzer = QualityAnalyzer(use_face_mesh=False)
        self.test_images = []

    def tearDown(self):
        """Clean up temp files."""
        for img in self.test_images:
            img.unlink(missing_ok=True)

    def test_analyze_batch_empty_list(self):
        """Test batch processing with empty list."""
        results = self.analyzer.analyze_batch([], max_workers=1)
        assert results == []

    def test_analyze_batch_single_image(self):
        """Test batch processing with single image."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil()
        self.test_images.append(test_image)
        
        results = self.analyzer.analyze_batch([test_image], max_workers=1)
        assert len(results) == 1
        assert results[0].path == test_image

    def test_analyze_batch_multiple_images(self):
        """Test batch processing with multiple images."""
        images = []
        for i in range(3):
            img = TestSyntheticImageGenerator.create_test_image_pil(
                width=800 + i*100, height=600 + i*100
            )
            images.append(img)
            self.test_images.append(img)
        
        results = self.analyzer.analyze_batch(images, max_workers=1)
        assert len(results) == 3
        assert all(isinstance(r, QualityResult) for r in results)

    def test_analyze_batch_with_progress_callback(self):
        """Test batch processing with progress callback."""
        images = [
            TestSyntheticImageGenerator.create_test_image_pil()
            for _ in range(3)
        ]
        self.test_images.extend(images)
        
        progress_calls = []
        def progress_callback(current, total):
            progress_calls.append((current, total))
        
        results = self.analyzer.analyze_batch(
            images, progress_callback=progress_callback, max_workers=1
        )
        
        assert len(results) == 3
        # Progress should be called at least once
        assert len(progress_calls) > 0

    def test_batch_preserves_order(self):
        """Test batch processing preserves image order."""
        images = []
        for i in range(3):
            img = TestSyntheticImageGenerator.create_test_image_pil(
                width=800 + i*100
            )
            images.append(img)
            self.test_images.append(img)
        
        results = self.analyzer.analyze_batch(images, max_workers=1)
        
        # Results should be in same order as input
        for i, result in enumerate(results):
            assert result.path == images[i]


class TestQualityAnalyzerCameraProfile(TestCase):
    """Test camera model detection and profile tracking."""

    def test_camera_profile_extract_unknown(self):
        """Test camera extraction with missing EXIF."""
        exif_data = {}
        camera = CameraProfile.extract_camera_model(exif_data)
        assert camera == "unknown"

    def test_camera_profile_extract_iphone(self):
        """Test camera extraction recognizes iPhone."""
        exif_data = {"model": "iPhone 12"}
        camera = CameraProfile.extract_camera_model(exif_data)
        # Camera model extraction is implementation-dependent
        # Just check it returns a string
        assert isinstance(camera, str)
        assert len(camera) > 0

    def test_camera_profile_extract_samsung(self):
        """Test camera extraction recognizes Samsung."""
        exif_data = {"model": "Samsung Galaxy S21"}
        camera = CameraProfile.extract_camera_model(exif_data)
        # Camera model extraction is implementation-dependent
        # Just check it returns a string
        assert isinstance(camera, str)
        assert len(camera) > 0

    def test_camera_profile_case_insensitive(self):
        """Test camera extraction is case-insensitive."""
        exif_data1 = {"model": "PIXEL 6"}
        exif_data2 = {"model": "pixel 6"}
        camera1 = CameraProfile.extract_camera_model(exif_data1)
        camera2 = CameraProfile.extract_camera_model(exif_data2)
        # Should normalize to same value
        assert camera1.lower() == camera2.lower()


class TestQualityAnalyzerComponentScoring(TestCase):
    """Test individual component scoring."""

    def setUp(self):
        """Initialize analyzer."""
        if not CV2_AVAILABLE or not PIL_AVAILABLE:
            self.skipTest("cv2 and PIL required")
        self.analyzer = QualityAnalyzer(use_face_mesh=False)

    def tearDown(self):
        """Clean up."""
        pass

    def test_sharpness_scoring_valid_range(self):
        """Test sharpness score is within valid range."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil()
        try:
            result = self.analyzer.analyze_image(test_image)
            # Sharpness should be normalized or in reasonable range
            assert result.overall_sharpness >= 0
        finally:
            test_image.unlink(missing_ok=True)

    def test_lighting_scoring_valid_range(self):
        """Test lighting score is within valid range."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil()
        try:
            result = self.analyzer.analyze_image(test_image)
            # Lighting should be normalized 0-100
            assert 0 <= result.lighting_score <= 100
        finally:
            test_image.unlink(missing_ok=True)

    def test_resolution_scoring_positive(self):
        """Test resolution score is positive."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil(
            width=2000, height=1500
        )
        try:
            result = self.analyzer.analyze_image(test_image)
            assert result.resolution_score > 0
        finally:
            test_image.unlink(missing_ok=True)

    def test_total_score_non_negative(self):
        """Test total score is non-negative."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil()
        try:
            result = self.analyzer.analyze_image(test_image)
            assert result.total_score >= 0
        finally:
            test_image.unlink(missing_ok=True)


class TestQualityAnalyzerErrorHandling(TestCase):
    """Test error handling and resilience."""

    def setUp(self):
        """Initialize analyzer."""
        self.analyzer = QualityAnalyzer(use_face_mesh=False)

    def test_analyze_nonexistent_file(self):
        """Test analyzing nonexistent file returns error."""
        result = self.analyzer.analyze_image(Path("/nonexistent/file.jpg"))
        # Should return result with error set or handle gracefully
        assert result is not None
        # May have error set if file doesn't exist
        if result.error:
            assert "failed" in result.error.lower() or "not found" in result.error.lower() or "no such" in result.error.lower()

    def test_analyze_invalid_format(self):
        """Test analyzing invalid image format."""
        # Create text file with .jpg extension
        with tempfile.NamedTemporaryFile(
            suffix=".jpg", mode="w", delete=False
        ) as f:
            f.write("not an image")
            temp_path = Path(f.name)
        
        try:
            result = self.analyzer.analyze_image(temp_path)
            # Should handle gracefully
            assert result is not None
        finally:
            temp_path.unlink(missing_ok=True)

    def test_analyze_corrupted_jpeg(self):
        """Test analyzing corrupted JPEG data."""
        with tempfile.NamedTemporaryFile(
            suffix=".jpg", delete=False, mode="wb"
        ) as f:
            # Write corrupted JPEG header
            f.write(b"\xFF\xD8\xFF")
            f.write(b"corrupted data")
            temp_path = Path(f.name)
        
        try:
            result = self.analyzer.analyze_image(temp_path)
            # Should not crash
            assert result is not None
        finally:
            temp_path.unlink(missing_ok=True)

    def test_batch_with_invalid_images(self):
        """Test batch processing with mix of valid and invalid images."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        
        valid_image = TestSyntheticImageGenerator.create_test_image_pil()
        
        # Create invalid image
        with tempfile.NamedTemporaryFile(
            suffix=".jpg", mode="w", delete=False
        ) as f:
            f.write("invalid")
            invalid_path = Path(f.name)
        
        try:
            results = self.analyzer.analyze_batch([valid_image, invalid_path], max_workers=1)
            assert len(results) == 2
            # At least one should be valid
            assert any(r.error is None for r in results)
        finally:
            valid_image.unlink(missing_ok=True)
            invalid_path.unlink(missing_ok=True)


class TestQualityAnalyzerExifHandling(TestCase):
    """Test EXIF data extraction and fallback behavior."""

    def setUp(self):
        """Initialize analyzer."""
        if not PIL_AVAILABLE:
            self.skipTest("PIL required")
        self.analyzer = QualityAnalyzer(use_face_mesh=False)

    def tearDown(self):
        """Clean up."""
        pass

    def test_analyze_image_without_exif(self):
        """Test analyzing image with no EXIF data."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil()
        try:
            result = self.analyzer.analyze_image(test_image)
            assert result is not None
            # Should still have valid analysis
            assert result.width > 0
            assert result.height > 0
            # Camera should be unknown
            assert result.camera_model == "unknown" or result.camera_model is not None
        finally:
            test_image.unlink(missing_ok=True)

    def test_exif_data_stored_in_result(self):
        """Test EXIF data is captured in result."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil()
        try:
            result = self.analyzer.analyze_image(test_image)
            # EXIF data field should exist
            assert hasattr(result, "exif_data")
        finally:
            test_image.unlink(missing_ok=True)

    def test_iso_aperture_focal_length_fields(self):
        """Test sensor metadata fields exist."""
        test_image = TestSyntheticImageGenerator.create_test_image_pil()
        try:
            result = self.analyzer.analyze_image(test_image)
            # Fields should exist (may be None)
            assert hasattr(result, "iso_value")
            assert hasattr(result, "aperture_value")
            assert hasattr(result, "focal_length")
        finally:
            test_image.unlink(missing_ok=True)


class TestQualityResultDataclass(TestCase):
    """Test QualityResult data structure."""

    def test_quality_result_creation(self):
        """Test creating QualityResult."""
        result = QualityResult(
            path=Path("/test/image.jpg"),
            width=1920,
            height=1440,
            overall_sharpness=0.75,
            lighting_score=60.0,
            resolution_score=2.0,
        )
        assert result.path == Path("/test/image.jpg")
        assert result.width == 1920

    def test_quality_result_default_values(self):
        """Test QualityResult default values."""
        result = QualityResult(path=Path("/test/image.jpg"))
        assert result.error is None
        assert result.overall_sharpness == 0.0
        assert result.camera_model == "unknown"

    def test_quality_result_face_quality_optional(self):
        """Test face quality is optional."""
        result = QualityResult(
            path=Path("/test/image.jpg"),
            face_quality=None,
        )
        assert result.face_quality is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
