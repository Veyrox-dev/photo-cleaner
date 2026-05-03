"""
ExifGroupingEngine: Orchestriert Gruppierung nach Ort + Datum.

Extrahiert EXIF-Metadaten, erstellt geografische Gruppen,
triggert Reverse Geocoding und speichert Ergebnisse.
"""

import logging
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class ExifGroupingEngine(QObject):
    """
    Orchestriert Gruppierung nach Ort + Datum.
    
    Workflow:
        1. Extrahiere EXIF-Daten (GPS, Datum)
        2. Erstelle Gruppen nach (lat, lon) + Date
        3. Reverse Geocoding für jede Gruppe
        4. Speichere in DB
    """
    
    # Signale
    grouping_started = Signal(int)  # count: int
    grouping_progress = Signal(int, int)  # current, total
    grouping_completed = Signal(dict)  # result_summary
    grouping_error = Signal(str)  # error_message
    
    def __init__(self, db_path: Path, geocoding_cache, geocoder):
        """
        Initialisiert die Engine.
        
        Args:
            db_path: Path zur SQLite DB
            geocoding_cache: GeocodingCache-Instanz
            geocoder: NominatimGeocoder-Instanz
        """
        super().__init__()
        self.db_path = db_path
        self.geocoding_cache = geocoding_cache
        self.geocoder = geocoder
        self._is_running = False
        
        logger.debug("ExifGroupingEngine initialisiert")
    
    def group_images(self, image_list: List, scan_session_id: Optional[str] = None):
        """
        Gruppiert Bilder nach Ort + Datum.
        
        Args:
            image_list: Liste von Image-Objekten mit EXIF-Daten
            scan_session_id: Optional, für DB-Verknüpfung
        """
        if self._is_running:
            logger.warning("ExifGroupingEngine: Grouping läuft bereits")
            return
        
        if not image_list:
            logger.info("ExifGroupingEngine: Leere Liste, keine Grouping")
            return
        
        self._is_running = True
        self.grouping_started.emit(len(image_list))
        
        try:
            logger.info(f"ExifGroupingEngine: Starten Grouping für {len(image_list)} Bilder")
            
            # 1. Extrahiere EXIF-Metadaten
            exif_data = self._extract_exif_data(image_list)
            logger.info(f"ExifGroupingEngine: {len(exif_data)} EXIF-Datensätze extrahiert")
            
            # 2. Erstelle Gruppen
            groups = self._create_groups(exif_data)
            logger.info(f"ExifGroupingEngine: {len(groups)} Gruppen erstellt")
            
            # 3. Reverse Geocoding für jede Gruppe
            for idx, group in enumerate(groups):
                self._geocode_group(group)
                self.grouping_progress.emit(idx, len(groups))
            
            logger.info(f"ExifGroupingEngine: Geocoding abgeschlossen")
            
            # 4. Speichere in DB
            saved_count = self._save_groups_to_db(groups, scan_session_id)
            
            result = {
                "total_images": len(image_list),
                "exif_extracted": len(exif_data),
                "groups_created": len(groups),
                "groups_saved": saved_count,
                "timestamp": datetime.now().isoformat(),
                "source": "exif_grouping"
            }
            
            logger.info(f"ExifGroupingEngine: Grouping abgeschlossen. "
                       f"{result['total_images']} Bilder in {result['groups_created']} Gruppen")
            self.grouping_completed.emit(result)
        
        except Exception as e:
            logger.error(f"ExifGroupingEngine: Fehler: {e}", exc_info=True)
            self.grouping_error.emit(str(e))
        
        finally:
            self._is_running = False
    
    def _extract_exif_data(self, image_list: List) -> Dict:
        """
        Extrahiere EXIF-Daten aus Bildern.
        
        [FILL: Integration mit existierendem EXIF-Extractor (RatingWorkerThread)]
        
        Erwartete Struktur pro Bild:
        {
            "image_id": "...",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "date_original": "2026-05-02",
            "camera_model": "Canon EOS R6"
        }
        
        Args:
            image_list: Liste von Image-Objekten
        
        Returns:
            Dict: {image_id: exif_dict, ...}
        """
        exif_data: Dict[int, Dict] = {}

        for image in image_list:
            try:
                image_path = Path(image)
                if not image_path.exists():
                    continue

                file_id = self._get_file_id_for_path(image_path)
                if file_id is None:
                    continue

                lat, lon, date_original, camera_model = self._read_exif_fields(image_path)
                exif_data[file_id] = {
                    "image_id": file_id,
                    "latitude": lat,
                    "longitude": lon,
                    "date_original": date_original,
                    "camera_model": camera_model,
                }
            except Exception as e:
                logger.warning(f"ExifGroupingEngine: Fehler beim EXIF-Lesen von {image}: {e}")
                continue

        return exif_data
    
    def _create_groups(self, exif_data: Dict) -> List[Dict]:
        """
        Erstelle Gruppen nach (lat, lon) + Date.
        
        Gruppierungs-Key: "latitude_longitude_date"
        Fallback ohne GPS: "no_gps_date"
        
        Args:
            exif_data: Dict mit EXIF-Metadaten
        
        Returns:
            Liste von Group-Dicts
        """
        groups_dict = defaultdict(list)
        
        for image_id, exif in exif_data.items():
            try:
                # Extrahiere Koordinaten und Datum
                lat = exif.get('latitude')
                lon = exif.get('longitude')
                date_str = exif.get('date_original', '1970-01-01')
                
                # Erstelle Group-Key
                if lat is not None and lon is not None:
                    # GPS vorhanden: "lat_lon_date"
                    group_key = f"{lat:.4f}_{lon:.4f}_{date_str}"
                else:
                    # GPS fehlt: "no_gps_date"
                    group_key = f"no_gps_{date_str}"
                
                groups_dict[group_key].append(image_id)
            
            except Exception as e:
                logger.warning(f"ExifGroupingEngine: Fehler beim Group-Key-Erstellen: {e}")
                groups_dict["error"].append(image_id)
        
        # Konvertiere zu GeoGroup-Objekten
        groups = []
        for key, ids in groups_dict.items():
            group = {
                "group_key": key,
                "image_ids": ids,
                "count": len(ids),
                "location_name": None,  # Wird später durch Geocoding gefüllt
                "city": None,
                "country": None
            }
            groups.append(group)
        
        logger.info(f"ExifGroupingEngine: {len(groups)} Gruppen erstellt")
        return groups
    
    def _geocode_group(self, group: Dict):
        """
        Reverse Geocoding für eine Gruppe.
        
        Args:
            group: Group-Dict mit group_key, image_ids
        """
        group_key = group["group_key"]
        
        # Fallback: Keine GPS-Daten
        if group_key.startswith("no_gps"):
            group["location_name"] = "Ohne Ort-Info"
            logger.debug(f"ExifGroupingEngine: Group {group_key} → No GPS")
            return
        
        # Extrahiere lat/lon aus group_key
        try:
            parts = group_key.split("_")
            lat, lon = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            group["location_name"] = "Ungültige Koordinaten"
            logger.warning(f"ExifGroupingEngine: Ungültige Koordinaten in {group_key}")
            return
        
        # Versuche zu geocoden (Cache first)
        location = self.geocoding_cache.get((lat, lon))
        
        if location is None:
            # API-Call
            location = self.geocoder.reverse_geocode(lat, lon)
            if location:
                self.geocoding_cache.set((lat, lon), location)
                logger.debug(f"ExifGroupingEngine: Geocoded {group_key} → {location.get('city')}")
        
        # Setze Ort auf Group
        if location:
            group["location_name"] = f"{location.get('city', 'Unknown')}, {location.get('country', '')}"
            group["city"] = location.get('city')
            group["country"] = location.get('country')
        else:
            group["location_name"] = "Geocoding Fehler"
    
    def _save_groups_to_db(self, groups: List[Dict], scan_session_id: Optional[str] = None) -> int:
        """
        Speichere Gruppen in DB.

        - UPDATE files.exif_location_name für jedes Bild
        - INSERT OR REPLACE in geo_groups (UNIQUE group_key)
        - INSERT OR IGNORE in geo_group_images (file_id → geo_group_id)

        Args:
            groups: Liste von Group-Dicts
            scan_session_id: Optional Session-ID

        Returns:
            Anzahl gespeicherter Gruppen
        """
        logger.debug(f"ExifGroupingEngine: Speichere {len(groups)} Gruppen in DB")

        saved = 0
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            for group in groups:
                group_key = group["group_key"]
                location_name = group.get("location_name") or ""
                city = group.get("city")
                country = group.get("country")
                image_ids = group.get("image_ids", [])

                # Derive lat/lon + date range from group_key
                lat: Optional[float] = None
                lon: Optional[float] = None
                date_val: Optional[str] = None
                if not group_key.startswith("no_gps") and not group_key.startswith("error"):
                    try:
                        parts = group_key.split("_")
                        lat = float(parts[0])
                        lon = float(parts[1])
                        date_val = parts[2] if len(parts) > 2 else None
                    except (ValueError, IndexError):
                        pass
                else:
                    # no_gps_<date> — extract date after second underscore
                    try:
                        date_val = group_key.split("_", 2)[2]
                    except IndexError:
                        pass

                # INSERT OR REPLACE into geo_groups
                cursor.execute(
                    """
                    INSERT INTO geo_groups
                        (scan_session_id, group_key, latitude, longitude,
                         location_name, city, country,
                         date_start, date_end, image_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(group_key) DO UPDATE SET
                        location_name = excluded.location_name,
                        city          = excluded.city,
                        country       = excluded.country,
                        image_count   = excluded.image_count,
                        scan_session_id = excluded.scan_session_id
                    """,
                    (
                        scan_session_id,
                        group_key,
                        lat,
                        lon,
                        location_name,
                        city,
                        country,
                        date_val,
                        date_val,
                        len(image_ids),
                    ),
                )
                geo_group_id = cursor.lastrowid

                # If it was an UPDATE (conflict), lastrowid is 0 — re-fetch the id
                if not geo_group_id:
                    cursor.execute(
                        "SELECT id FROM geo_groups WHERE group_key = ?",
                        (group_key,),
                    )
                    row = cursor.fetchone()
                    geo_group_id = row[0] if row else None

                # UPDATE files.exif_location_name + INSERT into geo_group_images
                for image_id in image_ids:
                    cursor.execute(
                        "UPDATE files SET exif_location_name = ? WHERE file_id = ?",
                        (location_name, int(image_id)),
                    )
                    if geo_group_id:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO geo_group_images (geo_group_id, file_id)
                            VALUES (?, ?)
                            """,
                            (geo_group_id, int(image_id)),
                        )

                saved += 1

            conn.commit()
            logger.info(f"ExifGroupingEngine: {saved} Gruppen in DB gespeichert")
            return saved
        except Exception as e:
            logger.error(f"ExifGroupingEngine: Fehler beim DB-Speichern: {e}", exc_info=True)
            if conn is not None:
                conn.rollback()
            return 0
        finally:
            if conn is not None:
                conn.close()

    def _get_file_id_for_path(self, image_path: Path) -> Optional[int]:
        """Liefert file_id aus DB für einen Bildpfad."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT file_id FROM files WHERE path = ?", (str(image_path),))
            row = cursor.fetchone()
            if not row:
                return None
            return int(row[0])
        except Exception:
            logger.debug("ExifGroupingEngine: file_id Lookup fehlgeschlagen", exc_info=True)
            return None
        finally:
            if conn is not None:
                conn.close()

    @staticmethod
    def _rational_to_float(value) -> Optional[float]:
        """Konvertiert EXIF-Rational/Tuple zu float."""
        try:
            if isinstance(value, tuple) and len(value) == 2:
                num, den = value
                if den == 0:
                    return None
                return float(num) / float(den)
            return float(value)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    def _dms_to_decimal(self, dms_values, ref: Optional[str]) -> Optional[float]:
        """Konvertiert GPS-DMS Werte in Dezimalgrad."""
        try:
            if not dms_values or len(dms_values) < 3:
                return None

            deg = self._rational_to_float(dms_values[0])
            minute = self._rational_to_float(dms_values[1])
            sec = self._rational_to_float(dms_values[2])
            if deg is None or minute is None or sec is None:
                return None

            decimal = deg + (minute / 60.0) + (sec / 3600.0)
            if ref and str(ref).upper() in ("S", "W"):
                decimal = -decimal
            return decimal
        except Exception:
            return None

    def _read_exif_fields(self, image_path: Path):
        """Liest GPS, Datum und Kameramodell aus EXIF."""
        latitude = None
        longitude = None
        date_original = "1970-01-01"
        camera_model = None

        with Image.open(image_path) as img:
            exif_raw = img.getexif()
            if not exif_raw:
                return latitude, longitude, date_original, camera_model

            for tag_id, value in exif_raw.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                if tag_name in ("DateTimeOriginal", "DateTime", "DateTimeDigitized") and isinstance(value, str):
                    date_original = value.split(" ")[0].replace(":", "-")
                elif tag_name in ("Model", "Camera Model"):
                    camera_model = str(value)

            gps_ifd = exif_raw.get_ifd(0x8825)
            if gps_ifd:
                gps_mapped = {}
                for k, v in gps_ifd.items():
                    gps_tag_name = GPSTAGS.get(k, k)
                    gps_mapped[gps_tag_name] = v

                lat_dms = gps_mapped.get("GPSLatitude")
                lat_ref = gps_mapped.get("GPSLatitudeRef")
                lon_dms = gps_mapped.get("GPSLongitude")
                lon_ref = gps_mapped.get("GPSLongitudeRef")

                latitude = self._dms_to_decimal(lat_dms, lat_ref)
                longitude = self._dms_to_decimal(lon_dms, lon_ref)

        return latitude, longitude, date_original, camera_model
    
    def is_running(self) -> bool:
        """Gibt an, ob Grouping gerade läuft."""
        return self._is_running
