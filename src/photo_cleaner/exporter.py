"""
Export-Modul für strukturiertes Kopieren von ausgewählten Bildern.
Zielstruktur: Output/YYYY/MM/DD/image.jpg basierend auf EXIF-Daten.

v0.5.3: StreamingExporter zum speicherschonenden ZIP-Export (50k+ Dateien).
"""

import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Callable

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    TAGS = None

logger = logging.getLogger(__name__)


def _extract_date_from_path(image_path: Path) -> datetime:
    """Extract a best-effort capture date from EXIF or filesystem metadata."""
    if PIL_AVAILABLE and Image:
        try:
            with Image.open(image_path) as img:
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if tag_name in ["DateTimeOriginal", "DateTime", "DateTimeDigitized"]:
                            try:
                                date = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                logger.debug(f"EXIF date for {image_path.name}: {date} (from {tag_name})")
                                return date
                            except ValueError:
                                continue
        except Exception as e:
            logger.debug(f"EXIF extraction failed for {image_path.name}: {e}")

    mtime = image_path.stat().st_mtime
    date = datetime.fromtimestamp(mtime)
    logger.debug(f"Fallback date for {image_path.name}: {date} (from mtime)")
    return date


def _build_dated_relative_path(source: Path, date: datetime, used_paths: set[str] | None = None) -> str:
    """Build a YYYY/MM/DD relative export path with collision avoidance."""
    year = f"{date.year:04d}"
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"
    base_dir = Path(year) / month / day
    candidate = base_dir / source.name

    if used_paths is None:
        return candidate.as_posix()

    counter = 1
    while candidate.as_posix() in used_paths:
        candidate = base_dir / f"{source.stem}_{counter}{source.suffix}"
        counter += 1

    used_paths.add(candidate.as_posix())
    return candidate.as_posix()


class Exporter:
    """Exportiert ausgewählte Bilder in strukturierte Ordner.

    ``mode`` steuert die Zielstruktur:
    - ``"date"``  (Standard): Output/YYYY/MM/DD/bild.jpg
    - ``"flat"``          : Output/bild.jpg  (keine Unterordner)
    - ``"year_month"``    : Output/YYYY/MM/bild.jpg
    - ``"year"``          : Output/YYYY/bild.jpg
    """

    MODES = ("date", "flat", "year_month", "year")

    def __init__(self, output_base: Path, mode: str = "date"):
        """
        Args:
            output_base: Basis-Ordner für Export (z.B. /Output)
            mode: Export-Strukturmodus (date | flat | year_month | year)
        """
        self.output_base = output_base
        self.mode = mode if mode in self.MODES else "date"
        self.output_base.mkdir(parents=True, exist_ok=True)

    def export_file(self, source: Path) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Exportiert eine Datei in die YYYY/MM/DD Struktur.

        Args:
            source: Quelldatei

        Returns:
            (success, target_path, error_message)
        """
        try:
            # P1.9: Check if file is accessible/locked before attempting to copy
            try:
                # Try to open the file to check if it's locked (Windows/file-system)
                with open(source, 'rb') as f:
                    pass  # Just checking if readable
            except (PermissionError, IOError) as e:
                error_msg = f"Cannot access file (may be locked or permissions denied): {source}"
                logger.warning(error_msg)
                return False, None, error_msg
            
            # Datum ermitteln
            date = self._extract_date(source)

            # Zielordner je nach gewähltem Modus
            if self.mode == "flat":
                target_dir = self.output_base
            elif self.mode == "year":
                target_dir = self.output_base / f"{date.year:04d}"
            elif self.mode == "year_month":
                target_dir = self.output_base / f"{date.year:04d}" / f"{date.month:02d}"
            else:  # "date" (default)
                year = f"{date.year:04d}"
                month = f"{date.month:02d}"
                day = f"{date.day:02d}"
                target_dir = self.output_base / year / month / day
            target_dir.mkdir(parents=True, exist_ok=True)

            # Zieldatei
            target_path = target_dir / source.name

            # Kollisionsvermeidung
            counter = 1
            while target_path.exists():
                stem = source.stem
                suffix = source.suffix
                target_path = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            # Kopieren (with P1.9 error handling for locked files)
            try:
                shutil.copy2(source, target_path)
            except (PermissionError, IOError) as e:
                error_msg = f"Cannot copy file (locked or permission denied): {source}"
                logger.warning(error_msg)
                return False, None, error_msg
            
            logger.info(f"Exported: {source} → {target_path}")
            return True, target_path, None

        except Exception as e:
            error_msg = f"Export failed for {source}: {e}"
            logger.exception(error_msg)
            return False, None, error_msg

    def _extract_date(self, image_path: Path) -> datetime:
        """
        Extrahiert Datum aus EXIF oder Dateisystem.

        Priorität:
        1. EXIF DateTimeOriginal
        2. EXIF DateTime
        3. EXIF CreateDate
        4. Dateisystem mtime

        Args:
            image_path: Pfad zur Bilddatei

        Returns:
            datetime-Objekt
        """
        return _extract_date_from_path(image_path)

    def export_files(self, sources: List[Path]) -> Tuple[int, int, List[str]]:
        """
        Exportiert mehrere Dateien.

        Args:
            sources: Liste von Quelldateien

        Returns:
            (success_count, failure_count, error_messages)
        """
        success_count = 0
        failure_count = 0
        errors = []

        for source in sources:
            success, _, error = self.export_file(source)
            if success:
                success_count += 1
            else:
                failure_count += 1
                if error:
                    errors.append(error)

        return success_count, failure_count, errors


class StreamingExporter:
    """Stream-basierter Export in ein ZIP-Archiv mit konstantem Speicherbedarf."""

    def __init__(self, output_base: Path, archive_name: Optional[str] = None):
        self.output_base = output_base
        self.output_base.mkdir(parents=True, exist_ok=True)
        if archive_name is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"photocleaner_export_{stamp}.zip"
        self.archive_path = self.output_base / archive_name
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Signalisiert Abbruch des Exports."""
        self._cancel_requested = True

    def export_files_streaming(
        self,
        sources: List[Path],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[int, int, List[str], Path, bool]:
        """Exportiert Dateien als ZIP, schreibt in kleinen Blöcken.

        Args:
            sources: Liste der Quellpfade
            progress_callback: Optionaler Callback(current, total, name)

        Returns:
            (success_count, failure_count, errors, archive_path, cancelled)
        """
        success_count = 0
        failure_count = 0
        errors: List[str] = []

        try:
            used_archive_paths: set[str] = set()
            with zipfile.ZipFile(self.archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                total = len(sources)
                for idx, source in enumerate(sources):
                    if self._cancel_requested:
                        logger.info("Streaming export cancelled by user")
                        return success_count, failure_count, errors, self.archive_path, True

                    try:
                        # Lese-Check (Datei offen/barrierefrei?)
                        with open(source, "rb") as fsrc:
                            export_date = _extract_date_from_path(source)
                            archive_name = _build_dated_relative_path(source, export_date, used_archive_paths)
                            info = zipfile.ZipInfo(filename=archive_name)
                            info.compress_type = zipfile.ZIP_DEFLATED
                            info.date_time = export_date.timetuple()[:6]
                            with zf.open(info, "w") as zdest:
                                for chunk in iter(lambda: fsrc.read(1024 * 1024), b""):
                                    zdest.write(chunk)
                        success_count += 1
                    except Exception as e:
                        failure_count += 1
                        err = f"Fehler beim Export {source}: {e}"
                        errors.append(err)
                        logger.warning(err)

                    if progress_callback:
                        progress_callback(idx + 1, total, source.name)

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Streaming export failed: {e}", exc_info=True)
            return success_count, failure_count, errors, self.archive_path, False

        return success_count, failure_count, errors, self.archive_path, False
