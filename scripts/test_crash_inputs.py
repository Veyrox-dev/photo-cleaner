"""Crash-test harness for invalid inputs.

Runs QualityAnalyzer against a set of malformed files and ensures no crashes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile
import secrets


def _ensure_repo_src_on_path() -> None:
    """Ensure direct script execution can import photo_cleaner from src/."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    src_str = str(src_path)
    if src_path.exists() and src_str not in sys.path:
        sys.path.insert(0, src_str)


def _write_bytes(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def main() -> int:
    _ensure_repo_src_on_path()
    os.environ.setdefault("PHOTOCLEANER_SKIP_HEAVY_DEPS", "1")
    os.environ.setdefault("PHOTOCLEANER_FACE_DETECTOR", "haar")
    os.environ.setdefault("PHOTOCLEANER_EYE_DETECTION_STAGE", "1")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

    try:
        from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
    except Exception as e:
        print(f"[ERROR] Failed to import QualityAnalyzer: {e}")
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        paths = []

        empty_file = tmp / "empty.jpg"
        _write_bytes(empty_file, b"")
        paths.append(empty_file)

        random_file = tmp / "random.bin"
        _write_bytes(random_file, secrets.token_bytes(256))
        paths.append(random_file)

        truncated_jpeg = tmp / "truncated.jpg"
        _write_bytes(truncated_jpeg, b"\xff\xd8\xff\xe0" + b"0" * 8)
        paths.append(truncated_jpeg)

        text_file = tmp / "not_image.txt"
        _write_bytes(text_file, b"not an image")
        paths.append(text_file)

        missing_file = tmp / "missing.jpg"
        paths.append(missing_file)

        analyzer = QualityAnalyzer(use_face_mesh=False)

        failed = False
        for path in paths:
            try:
                result = analyzer.analyze_image(path)
                if getattr(result, "error", None) is None:
                    print(f"[WARN] No error for invalid input: {path.name}")
            except Exception as e:
                failed = True
                print(f"[FAIL] Crash for {path.name}: {e}")

        if failed:
            return 1

    print("[OK] Crash input test completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
