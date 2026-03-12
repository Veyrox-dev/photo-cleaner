from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from photo_cleaner.config import AppConfig

logger = logging.getLogger(__name__)

_HAAR_CASCADE_DIR_CACHE: Path | None = None
_HAAR_CASCADE_DIR_CHECKED = False


def resolve_haar_cascade_dir(*, cv2_available: bool, cv2_module=None) -> Path | None:
    """Resolve OpenCV Haar cascade directory across dev/frozen layouts."""
    global _HAAR_CASCADE_DIR_CACHE, _HAAR_CASCADE_DIR_CHECKED

    if _HAAR_CASCADE_DIR_CHECKED:
        return _HAAR_CASCADE_DIR_CACHE

    _HAAR_CASCADE_DIR_CHECKED = True

    if not cv2_available:
        _HAAR_CASCADE_DIR_CACHE = None
        return _HAAR_CASCADE_DIR_CACHE

    candidates: list[Path] = []
    try:
        env_dir = os.environ.get("PHOTOCLEANER_HAAR_CASCADE_DIR") or os.environ.get("OPENCV_HAAR_CASCADE_DIR")
        if env_dir:
            candidates.append(Path(env_dir))
    except Exception:
        pass

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
            candidates.append(module_dir / "data")
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
        if not candidate.exists():
            continue
        if list(candidate.glob("haarcascade_*.xml")):
            _HAAR_CASCADE_DIR_CACHE = candidate
            logger.info("Haar cascades found at %s", candidate)
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
