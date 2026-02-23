"""Memory leak smoke test for QualityAnalyzer.

Runs repeated batch analysis and reports memory deltas.
"""
from __future__ import annotations

import gc
import os
import sys
import tempfile
import tracemalloc
import traceback
from pathlib import Path


def _write_test_image(path: Path, size: tuple[int, int]) -> None:
    try:
        from PIL import Image
    except Exception as e:
        raise RuntimeError(f"PIL not available: {e}")

    img = Image.new("RGB", size, color=(120, 140, 160))
    img.save(path, format="JPEG", quality=85)


def main() -> int:
    try:
        print("[INFO] Starting memory leak smoke test", flush=True)
        os.environ.setdefault("PHOTOCLEANER_SKIP_HEAVY_DEPS", "1")
        os.environ.setdefault("PHOTOCLEANER_FACE_DETECTOR", "haar")
        os.environ.setdefault("PHOTOCLEANER_EYE_DETECTION_STAGE", "1")
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

        try:
            print("[INFO] Importing QualityAnalyzer", flush=True)
            from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
        except BaseException as e:
            print(f"[ERROR] Failed to import QualityAnalyzer: {type(e).__name__}: {e}")
            traceback.print_exc()
            return 1

        print("[INFO] Building temporary images", flush=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            images = []
            for idx in range(6):
                path = tmp / f"img_{idx}.jpg"
                _write_test_image(path, (640 + idx * 10, 480 + idx * 10))
                images.append(path)

            analyzer = QualityAnalyzer(use_face_mesh=False)

            tracemalloc.start()
            baseline_current, baseline_peak = tracemalloc.get_traced_memory()

            rounds = 6
            for _ in range(rounds):
                print("[INFO] Running analysis batch", flush=True)
                for image_path in images:
                    analyzer.analyze_image(image_path)
                gc.collect()

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            delta_mb = (current - baseline_current) / (1024 * 1024)
            peak_mb = peak / (1024 * 1024)

            print(f"[INFO] Memory delta: {delta_mb:.2f} MB")
            print(f"[INFO] Peak memory: {peak_mb:.2f} MB")

            if delta_mb > 50:
                print("[FAIL] Memory growth exceeds 50 MB threshold")
                return 1

        print("[OK] Memory leak smoke test completed")
        return 0
    except BaseException as e:
        print(f"[ERROR] Memory leak test crashed: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
