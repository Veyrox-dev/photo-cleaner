"""
GeocodingCache: Hybrid Memory + SQLite Caching für Reverse-Geocoding.

Kombiniert schnelle Memory-Cache (LRU) mit persistenter SQLite-Speicherung.
TTL-Management: Automatisches Löschen abgelaufener Einträge.
"""

import logging
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class GeocodingCache:
    """
    Hybrid Memory (LRU) + SQLite Persistent Cache für Geocoding-Ergebnisse.
    
    - Memory: Schnell, für Hot-Data (LRU, max 1000 entries)
    - SQLite: Persistent, über Sessions hinweg
    - TTL: Automatisches Cleanup (default 7 Tage)
    """
    
    def __init__(self, db_path: Path, max_memory_entries: int = 1000, ttl_days: int = 7):
        """
        Initialisiert den Hybrid-Cache.
        
        Args:
            db_path: Path zur Cache-DB (SQLite)
            max_memory_entries: Memory-Cache Max-Einträge (LRU)
            ttl_days: Time-to-Live für Cache-Einträge in Tagen
        """
        self.db_path = Path(db_path)
        self.max_memory_entries = max_memory_entries
        self.ttl_days = ttl_days
        
        # Memory-LRU Cache: {coordinates_tuple: location_dict}
        self.memory_cache = OrderedDict()
        
        # Setup DB
        self._init_db()
        self._cleanup_expired()
        
        logger.debug(f"GeocodingCache initialisiert (TTL: {ttl_days}d, Memory: {max_memory_entries})")
    
    def get(self, coordinates: Tuple[float, float]) -> Optional[Dict]:
        """
        Hole Geocoding-Ergebnis aus Cache (Memory first, dann DB).
        
        Args:
            coordinates: (latitude, longitude) tuple
        
        Returns:
            Dict mit city, country, etc. oder None
        """
        if not isinstance(coordinates, tuple) or len(coordinates) != 2:
            return None
        
        # 1. Memory-Cache prüfen
        if coordinates in self.memory_cache:
            logger.debug(f"GeocodingCache: Memory-Hit für {coordinates}")
            # Move to end (LRU)
            self.memory_cache.move_to_end(coordinates)
            return self.memory_cache[coordinates]
        
        # 2. DB-Cache prüfen
        result = self._get_from_db(coordinates)
        if result:
            logger.debug(f"GeocodingCache: DB-Hit für {coordinates}")
            # Add to memory-cache
            self._add_to_memory(coordinates, result)
            return result
        
        logger.debug(f"GeocodingCache: Cache-Miss für {coordinates}")
        return None
    
    def set(self, coordinates: Tuple[float, float], location_data: Dict):
        """
        Speichere Geocoding-Ergebnis im Cache (Memory + DB).
        
        Args:
            coordinates: (latitude, longitude) tuple
            location_data: Dict mit city, country, address, etc.
        """
        if not isinstance(coordinates, tuple) or len(coordinates) != 2:
            return
        
        # Memory-Cache
        self._add_to_memory(coordinates, location_data)
        
        # DB-Cache
        self._save_to_db(coordinates, location_data)
    
    def _add_to_memory(self, coordinates: Tuple[float, float], data: Dict):
        """
        Füge zu Memory-LRU hinzu, evicte ältesten wenn Limit überschritten.
        
        Args:
            coordinates: Tuple
            data: Location-Dict
        """
        self.memory_cache[coordinates] = data
        self.memory_cache.move_to_end(coordinates)
        
        # LRU: Remove oldest wenn über limit
        if len(self.memory_cache) > self.max_memory_entries:
            removed = self.memory_cache.popitem(last=False)
            logger.debug(f"GeocodingCache: LRU-Eviction von {removed[0]}")
    
    def _init_db(self):
        """Initialisiere SQLite Cache-Tabelle."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS geocoding_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coordinates TEXT NOT NULL UNIQUE,
                    location_name TEXT,
                    city TEXT,
                    country TEXT,
                    raw_response TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ttl_hours INTEGER DEFAULT 168,
                    hits INTEGER DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_coordinates 
                ON geocoding_cache(coordinates)
            """)
            
            conn.commit()
            conn.close()
            
            logger.debug(f"GeocodingCache: DB initialisiert ({self.db_path})")
        
        except Exception as e:
            logger.error(f"GeocodingCache: Fehler beim DB-Setup: {e}", exc_info=True)
    
    def _get_from_db(self, coordinates: Tuple[float, float]) -> Optional[Dict]:
        """
        Hole Eintrag aus SQLite Cache.
        
        Args:
            coordinates: (lat, lon) tuple
        
        Returns:
            Dict oder None
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            coord_str = f"{coordinates[0]},{coordinates[1]}"
            
            cursor.execute("""
                SELECT location_name, city, country, raw_response, cached_at
                FROM geocoding_cache
                WHERE coordinates = ?
            """, (coord_str,))
            
            row = cursor.fetchone()
            
            if row:
                # Increment hits counter
                cursor.execute("""
                    UPDATE geocoding_cache
                    SET hits = hits + 1
                    WHERE coordinates = ?
                """, (coord_str,))
                conn.commit()

                result = {
                    "location_name": row[0],
                    "city": row[1],
                    "country": row[2],
                    "address": json.loads(row[3]) if row[3] else {},
                    "cached_at": row[4]
                }
                return result
            
            return None
        
        except Exception as e:
            logger.error(f"GeocodingCache: Fehler beim DB-Abruf: {e}", exc_info=True)
            return None
        finally:
            if conn is not None:
                conn.close()
    
    def _save_to_db(self, coordinates: Tuple[float, float], location_data: Dict):
        """
        Speichere Eintrag in SQLite Cache.
        
        Args:
            coordinates: (lat, lon) tuple
            location_data: Location-Dict
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            coord_str = f"{coordinates[0]},{coordinates[1]}"
            
            cursor.execute("""
                INSERT OR REPLACE INTO geocoding_cache
                (coordinates, location_name, city, country, raw_response, cached_at, ttl_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                coord_str,
                location_data.get("city", "Unknown"),
                location_data.get("city", ""),
                location_data.get("country", ""),
                json.dumps(location_data.get("address", {})),
                datetime.now().isoformat(),
                self.ttl_days * 24
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"GeocodingCache: Gespeichert → {coord_str}")
        
        except Exception as e:
            logger.error(f"GeocodingCache: Fehler beim DB-Speichern: {e}", exc_info=True)
    
    def _cleanup_expired(self):
        """Lösche abgelaufene Cache-Einträge (TTL überschritten)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(days=self.ttl_days)).isoformat()
            
            cursor.execute("""
                DELETE FROM geocoding_cache
                WHERE cached_at < ?
            """, (cutoff_time,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"GeocodingCache: {deleted_count} abgelaufene Einträge gelöscht")
        
        except Exception as e:
            logger.error(f"GeocodingCache: Fehler beim Cleanup: {e}", exc_info=True)
    
    def clear_all(self):
        """Leere gesamten Cache (Memory + DB)."""
        try:
            # Memory leeren
            self.memory_cache.clear()
            
            # DB leeren
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM geocoding_cache")
            conn.commit()
            conn.close()
            
            logger.info("GeocodingCache: Vollständig geleert (Memory + DB)")
        
        except Exception as e:
            logger.error(f"GeocodingCache: Fehler beim Clear: {e}", exc_info=True)
    
    def get_statistics(self) -> Dict:
        """Gebe Cache-Statistiken zurück."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM geocoding_cache")
            db_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(hits) FROM geocoding_cache")
            total_hits = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                "memory_entries": len(self.memory_cache),
                "db_entries": db_count,
                "total_hits": total_hits,
                "ttl_days": self.ttl_days,
                "memory_max": self.max_memory_entries
            }
        
        except Exception as e:
            logger.error(f"GeocodingCache: Fehler beim Statistics-Abruf: {e}", exc_info=True)
            return {}
