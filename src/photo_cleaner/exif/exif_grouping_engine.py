"""
ExifGroupingEngine: Orchestriert Gruppierung nach Ort + Datum.

Extrahiert EXIF-Metadaten, erstellt geografische Gruppen,
triggert Reverse Geocoding und speichert Ergebnisse.
"""

import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional
from PySide6.QtCore import QObject, pyqtSignal

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
    grouping_started = pyqtSignal(int)  # count: int
    grouping_progress = pyqtSignal(int, int)  # current, total
    grouping_completed = pyqtSignal(dict)  # result_summary
    grouping_error = pyqtSignal(str)  # error_message
    
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
        exif_data = {}
        
        for image in image_list:
            try:
                # [FILL: Lese EXIF-Metadaten aus Image-Objekt]
                # Beispiel:
                # exif = {
                #     "image_id": image.id,
                #     "latitude": image.exif.get("latitude"),
                #     "longitude": image.exif.get("longitude"),
                #     "date_original": image.exif.get("date_original"),
                #     "camera_model": image.exif.get("camera_model")
                # }
                # exif_data[image.id] = exif
                pass
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
        
        [FILL: DB-Integration - INSERT in geo_groups + geo_group_images]
        
        Args:
            groups: Liste von Group-Dicts
            scan_session_id: Optional Session-ID
        
        Returns:
            Anzahl gespeicherter Gruppen
        """
        # [FILL: SQL INSERT INTO geo_groups]
        logger.debug(f"ExifGroupingEngine: Speichere {len(groups)} Gruppen in DB")
        
        try:
            # Placeholder: Hier würde DB-Integration stattfinden
            saved = len(groups)
            logger.info(f"ExifGroupingEngine: {saved} Gruppen in DB gespeichert")
            return saved
        except Exception as e:
            logger.error(f"ExifGroupingEngine: Fehler beim DB-Speichern: {e}", exc_info=True)
            return 0
    
    def is_running(self) -> bool:
        """Gibt an, ob Grouping gerade läuft."""
        return self._is_running
