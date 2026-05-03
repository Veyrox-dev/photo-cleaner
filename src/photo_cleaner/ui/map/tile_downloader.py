"""TileDownloader — lädt OSM-Tiles für eine Bounding Box herunter.

Nur Tiles für tatsächlich benötigte Regionen werden heruntergeladen
(basierend auf GPS-Koordinaten der Fotos in der DB).

Tile-Quelle: OpenStreetMap (tile.openstreetmap.org) — kostenlos, CC-BY-SA.
Nutzungsbedingungen: https://operations.osmfoundation.org/policies/tiles/
  → Max. 2 Anfragen/Sekunde, User-Agent angeben.
"""
from __future__ import annotations

import logging
import math
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, Signal

from photo_cleaner.ui.map.tile_cache import TileCache
from photo_cleaner import __version__ as _APP_VERSION

logger = logging.getLogger(__name__)

# OSM-Tile-URL-Template (kann auf eigenen Tile-Server geändert werden)
DEFAULT_TILE_URL_TEMPLATE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

# Rate-Limiting: OSM-Policy — max. 2 req/s
DEFAULT_REQUEST_DELAY_S = 0.55

# User-Agent wie von OSM gefordert
_USER_AGENT = f"PhotoCleaner/{_APP_VERSION} (offline-map-cache; contact: map@photo-cleaner.app)"

# Zoom-Bereich: 0–14 ist optimal für Hotspot-Visualisierung
MIN_ZOOM = 0
MAX_ZOOM = 14


def _get_tile_url_template() -> str:
    template = os.getenv("PHOTOCLEANER_MAP_TILE_URL_TEMPLATE", DEFAULT_TILE_URL_TEMPLATE).strip()
    return template or DEFAULT_TILE_URL_TEMPLATE


def _is_osm_tile_host(url_template: str) -> bool:
    try:
        hostname = (urlparse(url_template).hostname or "").lower()
    except ValueError:
        return False
    return hostname.endswith("openstreetmap.org")


def _get_request_delay_s(url_template: str) -> float:
    raw_value = os.getenv("PHOTOCLEANER_MAP_REQUEST_DELAY_S", "").strip()
    if not raw_value:
        return DEFAULT_REQUEST_DELAY_S

    try:
        delay_s = max(0.0, float(raw_value))
    except ValueError:
        logger.warning(
            "Ungueltiger Wert fuer PHOTOCLEANER_MAP_REQUEST_DELAY_S=%r, verwende Standard %.2fs",
            raw_value,
            DEFAULT_REQUEST_DELAY_S,
        )
        return DEFAULT_REQUEST_DELAY_S

    if _is_osm_tile_host(url_template) and delay_s < DEFAULT_REQUEST_DELAY_S:
        logger.warning(
            "PHOTOCLEANER_MAP_REQUEST_DELAY_S=%.3f ist fuer OpenStreetMap zu aggressiv; "
            "verwende %.2fs gemaess OSM-Policy",
            delay_s,
            DEFAULT_REQUEST_DELAY_S,
        )
        return DEFAULT_REQUEST_DELAY_S

    return delay_s


@dataclass(frozen=True)
class BoundingBox:
    """WGS-84 Bounding Box."""
    south: float
    west: float
    north: float
    east: float

    @classmethod
    def from_points(cls, coords: list[tuple[float, float]]) -> "BoundingBox":
        """Erstellt BBox aus Liste von (lat, lon)-Punkten mit Padding."""
        if not coords:
            # Fallback: Deutschland
            return cls(south=47.2, west=5.8, north=55.1, east=15.1)
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        pad = 0.5  # ~50 km Puffer
        return cls(
            south=max(-85.0, min(lats) - pad),
            west=max(-180.0, min(lons) - pad),
            north=min(85.0, max(lats) + pad),
            east=min(180.0, max(lons) + pad),
        )

    def tile_count(self, max_zoom: int = MAX_ZOOM) -> int:
        """Schätzt die Anzahl der Tiles für diese BBox."""
        total = 0
        for z in range(MIN_ZOOM, max_zoom + 1):
            x0, y1 = _lat_lon_to_tile(self.north, self.west, z)
            x1, y0 = _lat_lon_to_tile(self.south, self.east, z)
            total += max(1, x1 - x0 + 1) * max(1, y1 - y0 + 1)
        return total

    def size_estimate_mb(self, max_zoom: int = MAX_ZOOM) -> float:
        """Grobe Größenschätzung: ~5 KB pro Tile im Schnitt."""
        return self.tile_count(max_zoom) * 5 / 1024


def _lat_lon_to_tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    """Konvertiert WGS-84 Koordinaten in Tile-Koordinaten (XYZ-Schema)."""
    lat_r = math.radians(lat)
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return (
        max(0, min(n - 1, x)),
        max(0, min(n - 1, y)),
    )


def _iter_tiles(bbox: BoundingBox, max_zoom: int) -> list[tuple[int, int, int]]:
    """Gibt alle (z, x, y)-Tiles für eine BBox zurück."""
    tiles = []
    for z in range(MIN_ZOOM, max_zoom + 1):
        x_min, y_min = _lat_lon_to_tile(bbox.north, bbox.west, z)
        x_max, y_max = _lat_lon_to_tile(bbox.south, bbox.east, z)
        if x_min > x_max:
            x_min, x_max = x_max, x_min
        if y_min > y_max:
            y_min, y_max = y_max, y_min
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                tiles.append((z, x, y))
    return tiles


class TileDownloadWorker(QThread):
    """Hintergrund-Thread: lädt Tiles herunter und speichert sie im Cache.

    Signals
    -------
    progress(downloaded, total):
        Fortschritt in Anzahl Tiles.
    status_message(msg):
        Lesbare Statusmeldung.
    finished_ok(downloaded_count):
        Download abgeschlossen.
    error_occurred(message):
        Fehler beim Download.
    """

    progress = Signal(int, int)
    status_message = Signal(str)
    finished_ok = Signal(int)
    error_occurred = Signal(str)

    def __init__(
        self,
        bbox: BoundingBox,
        cache: TileCache,
        max_zoom: int = MAX_ZOOM,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._bbox = bbox
        self._cache = cache
        self._max_zoom = max_zoom
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        tile_url_template = _get_tile_url_template()
        request_delay_s = _get_request_delay_s(tile_url_template)
        tiles = _iter_tiles(self._bbox, self._max_zoom)
        # Bereits gecachte Tiles überspringen
        missing = [(z, x, y) for z, x, y in tiles if not self._cache.has(z, x, y)]
        total = len(missing)
        logger.info(
            "TileDownloader: bbox S=%.4f W=%.4f N=%.4f E=%.4f, zoom<=%d, %d Tiles gesamt, %d Tiles fehlen, Quelle=%s, Delay=%.2fs",
            self._bbox.south,
            self._bbox.west,
            self._bbox.north,
            self._bbox.east,
            self._max_zoom,
            len(tiles),
            total,
            tile_url_template,
            request_delay_s,
        )

        if total == 0:
            self.status_message.emit("Alle Tiles bereits gecacht.")
            self.finished_ok.emit(0)
            return

        self.status_message.emit(
            f"Lade {total} Tiles herunter "
            f"(~{total * 5 / 1024:.1f} MB geschätzt) …"
        )
        logger.info("TileDownloader: %d Tiles fehlen, starte Download", total)

        downloaded = 0
        batch: list[tuple[int, int, int, bytes]] = []
        BATCH_SIZE = 50

        for z, x, y in missing:
            if self._cancelled:
                logger.info("TileDownloader: abgebrochen bei %d/%d", downloaded, total)
                break

            url = tile_url_template.format(z=z, x=x, y=y)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                batch.append((z, x, y, data))
                downloaded += 1

                if len(batch) >= BATCH_SIZE:
                    self._cache.put_batch(batch)
                    batch.clear()

                self.progress.emit(downloaded, total)
                if downloaded == 1 or downloaded % 25 == 0 or downloaded == total:
                    logger.info(
                        "TileDownloader: Fortschritt %d/%d Tiles (Cache: %.1f MB)",
                        downloaded,
                        total,
                        self._cache.size_mb(),
                    )
                if downloaded % 100 == 0:
                    self.status_message.emit(
                        f"{downloaded}/{total} Tiles geladen "
                        f"({self._cache.size_mb():.1f} MB)"
                    )

                if request_delay_s > 0:
                    time.sleep(request_delay_s)

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # Rate limit — kurz warten
                    logger.warning("OSM Rate-Limit, warte 10s …")
                    self.status_message.emit("OpenStreetMap begrenzt gerade die Anfragen. Warte 10 Sekunden ...")
                    time.sleep(10)
                else:
                    logger.warning("HTTP %d für %s — übersprungen", e.code, url)
            except Exception:
                logger.debug("Tile-Download fehlgeschlagen: %s", url, exc_info=True)

        if batch:
            self._cache.put_batch(batch)

        logger.info(
            "TileDownloader: abgeschlossen, %d/%d Tiles heruntergeladen, Cache jetzt %.1f MB",
            downloaded,
            total,
            self._cache.size_mb(),
        )
        self.finished_ok.emit(downloaded)
