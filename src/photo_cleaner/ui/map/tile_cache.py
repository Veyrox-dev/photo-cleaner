"""TileCache — lokaler SQLite-Cache für OSM-Raster-Tiles (MBTiles-Format).

Tiles werden im Standard-MBTiles-Format gespeichert:
    ~/.photo_cleaner/map_cache.mbtiles

Damit kann derselbe Cache auch mit externen Tools (QGIS, MB-Util etc.)
geöffnet werden.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Standard-Pfad für den Tile-Cache
DEFAULT_CACHE_PATH = Path.home() / ".photo_cleaner" / "map_cache.mbtiles"


class TileCache:
    """Lese-/Schreib-Zugriff auf einen lokalen MBTiles-Cache.

    MBTiles-Schema (vereinfacht):
        tiles(zoom_level, tile_column, tile_row, tile_data BLOB)
        metadata(name, value)

    WICHTIG: MBTiles verwendet TMS-Koordinaten (Y-Achse invertiert).
    """

    def __init__(self, cache_path: str | Path = DEFAULT_CACHE_PATH) -> None:
        self._path = Path(cache_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(self._path), check_same_thread=False)
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA synchronous=NORMAL")
        self._initialize()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        self._con.executescript("""
            CREATE TABLE IF NOT EXISTS tiles (
                zoom_level  INTEGER NOT NULL,
                tile_column INTEGER NOT NULL,
                tile_row    INTEGER NOT NULL,
                tile_data   BLOB    NOT NULL,
                PRIMARY KEY (zoom_level, tile_column, tile_row)
            );
            CREATE TABLE IF NOT EXISTS metadata (
                name  TEXT PRIMARY KEY,
                value TEXT
            );
            INSERT OR IGNORE INTO metadata VALUES ('name',   'PhotoCleaner Map Cache');
            INSERT OR IGNORE INTO metadata VALUES ('format', 'png');
            INSERT OR IGNORE INTO metadata VALUES ('version','1.0');
        """)
        self._con.commit()

    # ------------------------------------------------------------------
    # Lesen
    # ------------------------------------------------------------------

    def get(self, z: int, x: int, y: int) -> bytes | None:
        """Gibt Tile-Daten zurück oder None wenn nicht gecacht."""
        tms_y = (1 << z) - 1 - y   # XYZ → TMS
        row = self._con.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (z, x, tms_y),
        ).fetchone()
        return row[0] if row else None

    def has(self, z: int, x: int, y: int) -> bool:
        tms_y = (1 << z) - 1 - y
        row = self._con.execute(
            "SELECT 1 FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (z, x, tms_y),
        ).fetchone()
        return row is not None

    def count(self) -> int:
        """Anzahl gespeicherter Tiles."""
        row = self._con.execute("SELECT COUNT(*) FROM tiles").fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Schreiben
    # ------------------------------------------------------------------

    def put(self, z: int, x: int, y: int, data: bytes) -> None:
        """Speichert ein Tile (überschreibt vorhandene Einträge)."""
        tms_y = (1 << z) - 1 - y
        self._con.execute(
            "INSERT OR REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_data) "
            "VALUES (?, ?, ?, ?)",
            (z, x, tms_y, data),
        )
        self._con.commit()

    def put_batch(self, tiles: list[tuple[int, int, int, bytes]]) -> None:
        """Speichert viele Tiles auf einmal (effizienter als einzelne put-Aufrufe).

        tiles: Liste von (z, x, y, data)
        """
        converted = [(z, x, (1 << z) - 1 - y, data) for z, x, y, data in tiles]
        self._con.executemany(
            "INSERT OR REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_data) "
            "VALUES (?, ?, ?, ?)",
            converted,
        )
        self._con.commit()

    # ------------------------------------------------------------------
    # Statistik
    # ------------------------------------------------------------------

    def size_mb(self) -> float:
        """Dateigröße des Cache in MB."""
        try:
            return self._path.stat().st_size / (1024 * 1024)
        except OSError:
            return 0.0

    def close(self) -> None:
        self._con.close()
