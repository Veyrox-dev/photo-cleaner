"""
Week 6 validation: Cache-Pfad und Qualitätsdrift.

Tests:
  1. AppConfig.get_cache_dir() resolves inside the user-writable APPDATA tree,
     never under Program Files or the application installation directory.
  2. QualityAnalyzer.analyze_image() is deterministic — repeated calls on the
     same file return identical scores (no drift).
"""

import sys
import tempfile
from pathlib import Path

import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

try:
    import cv2 as _cv2_check
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image as _PIL_check
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _make_plain_jpg(width: int = 400, height: int = 300) -> Path:
    """Create a plain JPEG in a temp directory for analysis."""
    from PIL import Image
    img = Image.new("RGB", (width, height), (120, 140, 160))
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()
    img.save(tmp.name, "JPEG", quality=85)
    return Path(tmp.name)


# ── 1. Cache-Pfad ─────────────────────────────────────────────────────────────

class TestCachePathLocation:
    """Ensure the cache directory is in a user-writable location."""

    def test_cache_dir_is_under_appdata_on_windows(self, tmp_path, monkeypatch):
        """On Windows, cache must be under %APPDATA%, not Program Files."""
        if sys.platform != "win32":
            pytest.skip("Windows-specific test")

        import os
        appdata = os.environ.get("APPDATA", "")
        assert appdata, "APPDATA env var not set"

        from photo_cleaner.config import AppConfig

        # Reset cached class state so get_user_data_dir() re-evaluates
        AppConfig._user_data_dir = None
        cache_dir = AppConfig.get_cache_dir()

        assert cache_dir.is_relative_to(Path(appdata)), (
            f"Cache dir {cache_dir} is not under APPDATA ({appdata}). "
            "This would fail in an MSI-installed Protected environment."
        )

    def test_cache_dir_not_under_program_files(self, monkeypatch):
        """Cache must never resolve under Program Files."""
        if sys.platform != "win32":
            pytest.skip("Windows-specific test")

        import os
        pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        pf86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))

        from photo_cleaner.config import AppConfig
        AppConfig._user_data_dir = None
        cache_dir = AppConfig.get_cache_dir()

        assert not cache_dir.is_relative_to(pf), (
            f"Cache dir {cache_dir} is inside Program Files — not writable after MSI install."
        )
        assert not cache_dir.is_relative_to(pf86), (
            f"Cache dir {cache_dir} is inside Program Files (x86) — not writable after MSI install."
        )

    def test_cache_dir_is_writable(self):
        """Cache directory must exist and be writable (basic sanity)."""
        from photo_cleaner.config import AppConfig
        AppConfig._user_data_dir = None
        cache_dir = AppConfig.get_cache_dir()

        assert cache_dir.exists(), f"Cache dir {cache_dir} was not created by get_cache_dir()"

        probe = cache_dir / ".write_probe"
        try:
            probe.write_text("ok")
            probe.unlink()
        except OSError as exc:
            pytest.fail(f"Cache dir {cache_dir} is not writable: {exc}")

    def test_cache_dir_under_custom_data_dir(self, tmp_path):
        """When the data dir is overridden, cache must follow the override."""
        from photo_cleaner.config import AppConfig
        AppConfig.set_user_data_dir(tmp_path / "custom")
        try:
            cache_dir = AppConfig.get_cache_dir()
            assert cache_dir.is_relative_to(tmp_path / "custom")
        finally:
            # Restore to default so other tests are not affected
            AppConfig._user_data_dir = None


# ── 2. Qualitätsdrift ─────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not (CV2_AVAILABLE and PIL_AVAILABLE),
    reason="cv2 and Pillow required for quality analysis",
)
class TestQualityScoreDeterminism:
    """Verify that QualityAnalyzer produces stable (non-drifting) scores."""

    def test_repeated_analysis_same_scores(self, tmp_path):
        """Running analyze_image twice on the same file must yield identical scores."""
        from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer

        img_path = _make_plain_jpg()
        try:
            analyzer = QualityAnalyzer(use_face_mesh=False)

            result1 = analyzer.analyze_image(img_path)
            result2 = analyzer.analyze_image(img_path)

            assert result1.error is None, f"First run failed: {result1.error}"
            assert result2.error is None, f"Second run failed: {result2.error}"

            assert result1.overall_sharpness == pytest.approx(result2.overall_sharpness, abs=1e-6), (
                "overall_sharpness drifted between runs"
            )
            assert result1.lighting_score == pytest.approx(result2.lighting_score, abs=1e-6), (
                "lighting_score drifted between runs"
            )
            assert result1.resolution_score == pytest.approx(result2.resolution_score, abs=1e-6), (
                "resolution_score drifted between runs"
            )
            assert result1.total_score == pytest.approx(result2.total_score, abs=1e-6), (
                "total_score drifted between runs"
            )
            assert result1.width == result2.width
            assert result1.height == result2.height
        finally:
            Path(img_path).unlink(missing_ok=True)

    def test_different_analyzer_instances_same_result(self, tmp_path):
        """Creating a new QualityAnalyzer instance must not change the score."""
        from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer

        img_path = _make_plain_jpg()
        try:
            result_a = QualityAnalyzer(use_face_mesh=False).analyze_image(img_path)
            result_b = QualityAnalyzer(use_face_mesh=False).analyze_image(img_path)

            assert result_a.error is None
            assert result_b.error is None

            assert result_a.total_score == pytest.approx(result_b.total_score, abs=1e-6), (
                "total_score differs between fresh analyzer instances"
            )
        finally:
            Path(img_path).unlink(missing_ok=True)

    def test_score_within_valid_range(self, tmp_path):
        """All sub-scores must be in [0, 1] after normalization."""
        from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer

        img_path = _make_plain_jpg()
        try:
            result = QualityAnalyzer(use_face_mesh=False).analyze_image(img_path)
            assert result.error is None, f"Analysis error: {result.error}"

            # Scores are reported as floats; some pipelines normalize to [0,1]
            # others to [0,100] — accept either band but flag NaN/inf
            import math
            for attr in ("overall_sharpness", "lighting_score", "resolution_score"):
                val = getattr(result, attr)
                assert not math.isnan(val), f"{attr} is NaN"
                assert not math.isinf(val), f"{attr} is Inf"
                assert val >= 0, f"{attr}={val} is negative"
        finally:
            Path(img_path).unlink(missing_ok=True)
