from __future__ import annotations

import logging
from pathlib import Path

from photo_cleaner.ui.color_constants import get_label_foreground_color, get_semantic_colors

logger = logging.getLogger(__name__)


class ExifReader:
    """Reads and formats EXIF metadata from images."""

    @staticmethod
    def read_exif(image_path: Path) -> dict[str, str]:
        """Read EXIF data from an image file."""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            exif_data = {}

            with Image.open(image_path) as img:
                exif_data["Format"] = img.format or "Unknown"
                exif_data["Size"] = f"{img.width} x {img.height} px"
                exif_data["Mode"] = img.mode

                exif_raw = img.getexif()
                if not exif_raw:
                    return exif_data

                tag_map = {
                    "Make": "Camera Make",
                    "Model": "Camera Model",
                    "LensModel": "Lens",
                    "DateTime": "Date Taken",
                    "DateTimeOriginal": "Date Original",
                    "DateTimeDigitized": "Date Digitized",
                    "ExposureTime": "Shutter Speed",
                    "FNumber": "Aperture",
                    "ISOSpeedRatings": "ISO",
                    "FocalLength": "Focal Length",
                    "Flash": "Flash",
                    "WhiteBalance": "White Balance",
                    "ExposureProgram": "Exposure Mode",
                    "MeteringMode": "Metering Mode",
                    "Orientation": "Orientation",
                    "XResolution": "X Resolution",
                    "YResolution": "Y Resolution",
                    "Software": "Software",
                }

                for tag_id, value in exif_raw.items():
                    tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")

                    if tag_name == "ExposureTime" and isinstance(value, (tuple, list)):
                        if len(value) == 2 and value[1] != 0:
                            exif_data["Shutter Speed"] = f"{value[0]}/{value[1]} sec"
                    elif tag_name == "FNumber" and isinstance(value, (tuple, list)):
                        if len(value) == 2 and value[1] != 0:
                            f_value = value[0] / value[1]
                            exif_data["Aperture"] = f"f/{f_value:.1f}"
                    elif tag_name == "FocalLength" and isinstance(value, (tuple, list)):
                        if len(value) == 2 and value[1] != 0:
                            focal = value[0] / value[1]
                            exif_data["Focal Length"] = f"{focal:.1f} mm"
                    elif tag_name in tag_map:
                        exif_data[tag_map[tag_name]] = str(value)

                gps_info = exif_raw.get_ifd(0x8825)
                if gps_info:
                    exif_data["GPS"] = "Available"

            return exif_data

        except (OSError, IOError, ValueError) as e:
            logger.error("Could not read EXIF: %s", e, exc_info=True)
            return {"Error": f"Could not read EXIF: {e}"}

    @staticmethod
    def format_exif_html(exif_data: dict[str, str]) -> str:
        """Format EXIF data as HTML for UI display."""
        if not exif_data:
            return "<p><i>Keine EXIF-Daten verfuegbar</i></p>"

        html = "<table style='width: 100%; border-collapse: collapse;'>"

        basic_fields = ["Format", "Size", "Mode"]
        camera_fields = ["Camera Make", "Camera Model", "Lens"]
        exposure_fields = ["Shutter Speed", "Aperture", "ISO", "Focal Length"]
        other_fields = [
            key
            for key in exif_data.keys()
            if key not in basic_fields + camera_fields + exposure_fields
        ]

        def add_section(title: str, fields: list[str]) -> None:
            nonlocal html
            section_data = {key: value for key, value in exif_data.items() if key in fields}
            if section_data:
                label_color = get_label_foreground_color()
                info_color = get_semantic_colors()["info"]
                html += (
                    "<tr><td colspan='2' style='padding-top: 12px; font-weight: bold; "
                    f"color: {info_color};'>{title}</td></tr>"
                )
                for key, value in section_data.items():
                    html += (
                        f"<tr><td style='padding: 4px 12px; color: {label_color};'>{key}</td>"
                        f"<td style='padding: 4px;'>{value}</td></tr>"
                    )

        add_section("Bild", basic_fields)
        add_section("Kamera", camera_fields)
        add_section("Belichtung", exposure_fields)
        add_section("Andere", other_fields)

        html += "</table>"
        return html
