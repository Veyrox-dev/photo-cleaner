"""
NominatimGeocoder: Reverse Geocoding via OSM Nominatim.

Verwaltet API-Calls zu OpenStreetMap Nominatim mit Rate-Limiting,
Error-Handling und Retry-Logik.
"""

import logging
import time
import requests
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class NominatimGeocoder:
    """
    Reverse Geocoding using OpenStreetMap Nominatim.
    
    Konvertiert GPS-Koordinaten (Latitude, Longitude) zu Ort-Namen.
    
    Rate-Limits: 1 request/sec (per ToS)
    Kostenlos, keine API-Keys erforderlich
    """
    
    # API Config
    BASE_URL = "https://nominatim.openstreetmap.org/reverse"
    RATE_LIMIT_DELAY = 1.0  # 1 request per second
    TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # Exponential backoff
    
    def __init__(self, user_agent: str = "PhotoCleaner/0.8.7", timeout: int = 10):
        """
        Initialisiert den Geocoder.
        
        Args:
            user_agent: User-Agent Header (Nominatim erfordert dies)
            timeout: Request-Timeout in Sekunden
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        
        logger.debug(f"NominatimGeocoder initialisiert (timeout: {timeout}s)")
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        Reverse Geocoding: Koordinaten → Ort-Name.
        
        Args:
            latitude: Breite (-90 bis +90)
            longitude: Länge (-180 bis +180)
        
        Returns:
            Dict mit:
                - city: Stadtname
                - country: Ländername
                - address: Vollständige Adresse (dict)
                - display_name: Lesbare Bezeichnung
            
            oder None bei Fehler
        """
        # Validiere Koordinaten
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            logger.warning(f"NominatimGeocoder: Ungültige Koordinaten ({latitude}, {longitude})")
            return None
        
        # Rate-Limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - time_since_last)
        
        params = {
            "format": "json",
            "lat": latitude,
            "lon": longitude,
            "zoom": 10,
            "addressdetails": 1
        }
        
        # Retry-Loop
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(f"NominatimGeocoder: Reverse-Geocode ({latitude:.4f}, {longitude:.4f}) [attempt {attempt + 1}]")
                
                response = self.session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.timeout
                )
                
                self.last_request_time = time.time()
                
                # Success
                if response.status_code == 200:
                    data = response.json()
                    result = {
                        "city": data.get("address", {}).get("city", "Unknown"),
                        "country": data.get("address", {}).get("country", "Unknown"),
                        "address": data.get("address", {}),
                        "display_name": data.get("display_name", ""),
                        "cached_at": datetime.now().isoformat(),
                        "latitude": latitude,
                        "longitude": longitude
                    }
                    logger.debug(f"NominatimGeocoder: Erfolgreich geocoded → {result['city']}, {result['country']}")
                    return result
                
                # Rate-Limited
                elif response.status_code == 429:
                    wait_time = 5 * (attempt + 1)
                    logger.warning(f"NominatimGeocoder: Rate-Limited (429), warte {wait_time}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue
                
                # Other errors
                else:
                    logger.warning(f"NominatimGeocoder: HTTP {response.status_code} bei ({latitude:.4f}, {longitude:.4f})")
                    if response.status_code >= 500:
                        # Server Error, retry
                        wait_time = self.RETRY_DELAY_BASE ** (attempt + 1)
                        time.sleep(wait_time)
                        continue
                    else:
                        # Client Error, don't retry
                        return None
            
            except requests.Timeout:
                logger.warning(f"NominatimGeocoder: Timeout (attempt {attempt + 1}/{self.MAX_RETRIES})")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY_BASE ** (attempt + 1))
            
            except requests.ConnectionError as e:
                logger.warning(f"NominatimGeocoder: Connection Error: {e} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY_BASE ** (attempt + 1))
            
            except Exception as e:
                logger.error(f"NominatimGeocoder: Unerwarteter Fehler: {e}", exc_info=True)
                return None
        
        logger.error(f"NominatimGeocoder: Max retries exceeded für ({latitude:.4f}, {longitude:.4f})")
        return None
    
    def close(self):
        """Schließt die Session (Optional, für cleanup)."""
        if self.session:
            self.session.close()
            logger.debug("NominatimGeocoder: Session geschlossen")
