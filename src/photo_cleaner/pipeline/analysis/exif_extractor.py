from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ExifExtractor:
    """Centralized EXIF extraction and orientation handling."""

    MAX_EXIF_FIELDS = 500
    MAX_EXIF_JSON_SIZE = 100 * 1024
    SENSOR_TAGS = {
        "ISOSpeedRatings": "iso_value",
        "PhotographicSensitivity": "iso_value",
        "ApertureValue": "aperture_value",
        "FNumber": "f_number",
        "FocalLength": "focal_length",
        "ExposureTime": "exposure_time",
        "ShutterSpeedValue": "shutter_speed_value",
    }
    CAMERA_TAGS = ("Model", "Make", "DateTime", "DateTimeOriginal")

    def __init__(self, image_module: Any = None, cv2_module: Any = None):
        self._image_module = image_module
        self._cv2 = cv2_module

    @property
    def image_module(self):
        if self._image_module is None:
            from PIL import Image as Image_module

            self._image_module = Image_module
        return self._image_module

    @property
    def cv2(self):
        if self._cv2 is None:
            import cv2 as cv2_module

            self._cv2 = cv2_module
        return self._cv2

    def get_exif_orientation_from_pil(self, pil_image, image_path: Path) -> int:
        """Return EXIF orientation or 1 when not available."""
        try:
            from PIL.ExifTags import TAGS

            if pil_image is None:
                pil_image = self.image_module.open(image_path)
            exif_data = pil_image.getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    if tag_name == "Orientation":
                        return value
        except (OSError, IOError, AttributeError):
            logger.debug("Could not extract EXIF orientation", exc_info=True)
        return 1

    def extract_exif_data_from_pil(self, pil_image, image_path: Path) -> dict:
        """Extract validated EXIF and sensor metadata from PIL image."""
        try:
            from PIL.ExifTags import TAGS

            if pil_image is None:
                pil_image = self.image_module.open(image_path)

            exif_raw = pil_image.getexif()
            if not exif_raw:
                return {}

            if len(exif_raw) > self.MAX_EXIF_FIELDS:
                logger.warning(
                    f"EXIF too many fields ({len(exif_raw)}) for {image_path.name}, "
                    f"truncating to {self.MAX_EXIF_FIELDS}"
                )
                exif_raw = dict(list(exif_raw.items())[: self.MAX_EXIF_FIELDS])

            exif_dict = {}
            for tag_id, value in exif_raw.items():
                tag_name = TAGS.get(tag_id, str(tag_id))

                if tag_name in self.CAMERA_TAGS:
                    exif_dict[tag_name] = str(value)
                elif tag_name in self.SENSOR_TAGS:
                    self._parse_sensor_value(exif_dict, tag_name, value, image_path)

            self._enforce_exif_size_limit(exif_dict, image_path)

            if not exif_dict:
                logger.debug(f"No EXIF metadata found for {image_path.name}")

            return exif_dict
        except (OSError, IOError, AttributeError) as e:
            logger.debug(f"EXIF extraction failed for {image_path.name}: {e}", exc_info=True)
            return {}

    def extract_exif_data(self, image_path: Path) -> dict:
        """Extract EXIF by opening image internally."""
        try:
            pil_image = self.image_module.open(image_path)
            return self.extract_exif_data_from_pil(pil_image, image_path)
        except (OSError, IOError, AttributeError) as e:
            logger.debug(f"EXIF extraction failed for {image_path.name}: {e}", exc_info=True)
            return {}

    def rotate_image_from_exif(self, img, orientation: int):
        """Rotate/flip image according to EXIF orientation (1-8)."""
        cv2 = self.cv2

        if orientation == 1:
            return img
        if orientation == 2:
            return cv2.flip(img, 1)
        if orientation == 3:
            return cv2.rotate(img, cv2.ROTATE_180)
        if orientation == 4:
            return cv2.flip(img, 0)
        if orientation == 5:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        if orientation == 6:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        if orientation == 7:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        if orientation == 8:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return img

    def _parse_sensor_value(self, exif_dict: dict, tag_name: str, value: Any, image_path: Path) -> None:
        try:
            if tag_name in ("ISOSpeedRatings", "PhotographicSensitivity"):
                iso_val = int(value) if isinstance(value, (int, float)) else int(str(value))
                if 0 < iso_val <= 409600:
                    exif_dict["iso_value"] = iso_val
                else:
                    logger.debug(f"ISO value {iso_val} out of realistic range for {image_path.name}")
            elif tag_name in ("ApertureValue", "FNumber"):
                aperture_val = self._coerce_numeric(value, image_path, "aperture")
                if aperture_val is None:
                    return
                if 0.5 < aperture_val < 100:
                    exif_dict["aperture_value"] = round(aperture_val, 2)
                else:
                    logger.debug(f"Aperture value {aperture_val} out of realistic range for {image_path.name}")
            elif tag_name == "FocalLength":
                focal_val = self._coerce_numeric(value, image_path, "focal length")
                if focal_val is None:
                    return
                if 0 < focal_val < 5000:
                    exif_dict["focal_length"] = round(focal_val, 2)
                else:
                    logger.debug(f"Focal length {focal_val} out of realistic range for {image_path.name}")
            elif tag_name == "ExposureTime":
                exposure_val = self._coerce_numeric(value, image_path, "exposure time")
                if exposure_val is None:
                    return
                if 0.0001 < exposure_val < 60:
                    exif_dict["exposure_time"] = exposure_val
                else:
                    logger.debug(f"Exposure time {exposure_val} out of realistic range for {image_path.name}")
            elif tag_name == "ShutterSpeedValue":
                shutter_val = self._coerce_numeric(value, image_path, "shutter speed")
                if shutter_val is not None:
                    exif_dict["shutter_speed_value"] = shutter_val
        except (ValueError, ZeroDivisionError, TypeError) as parse_err:
            logger.debug(f"Failed to parse {tag_name}={value} for {image_path.name}: {parse_err}")

    def _coerce_numeric(self, value: Any, image_path: Path, metric_name: str) -> float | None:
        if isinstance(value, tuple) and len(value) == 2:
            if value[1] == 0:
                logger.debug(f"Invalid {metric_name} denominator 0 for {image_path.name}")
                return None
            return float(value[0]) / float(value[1])
        return float(value)

    def _enforce_exif_size_limit(self, exif_dict: dict, image_path: Path) -> None:
        try:
            exif_json = json.dumps(exif_dict, default=str)
            exif_size = len(exif_json.encode("utf-8"))
            if exif_size > self.MAX_EXIF_JSON_SIZE:
                logger.warning(
                    f"EXIF JSON too large ({exif_size} bytes) for {image_path.name}, "
                    "keeping only essential fields"
                )
                essential_keys = {"Model", "Make", "DateTime", "DateTimeOriginal"}
                retained = {k: v for k, v in exif_dict.items() if k in essential_keys}
                exif_dict.clear()
                exif_dict.update(retained)
        except Exception as e:
            logger.debug(f"Failed to check EXIF JSON size: {e}")
