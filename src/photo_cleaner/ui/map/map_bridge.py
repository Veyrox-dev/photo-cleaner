"""MapBridge — QWebChannel-Brücke zwischen Python und der Leaflet/MapLibre-Karte.

Python sendet Foto-GeoJSON an JS; JS meldet Viewport-Änderungen zurück.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

if TYPE_CHECKING:
    from PySide6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)


@dataclass
class PhotoMarker:
    """Minimale Repräsentation eines Foto-Markers für die Karte."""
    file_id: int
    lat: float
    lon: float
    path: str
    score: float | None = None
    location_name: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.file_id,
            "lat": self.lat,
            "lon": self.lon,
            "path": self.path,
            "score": self.score,
            "location_name": self.location_name or "",
        }


class MapBridge(QObject):
    """QObject, das über QWebChannel mit der Karte kommuniziert.

    Signals (Python → UI-Konsumenten)
    -----------------------------------
    viewport_changed(north, south, east, west):
        Wird ausgelöst, wenn der Nutzer die Karte verschiebt oder zoomt.
        Koordinaten als float in WGS-84 Dezimalgrad.

    marker_clicked(file_id):
        Wird ausgelöst, wenn der Nutzer einen Foto-Marker anklickt.
    """

    viewport_changed = Signal(float, float, float, float)
    marker_clicked = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._view: QWebEngineView | None = None

    # ------------------------------------------------------------------
    # Python → JavaScript
    # ------------------------------------------------------------------

    def load_photos(self, markers: list[PhotoMarker]) -> None:
        """Übergibt Foto-Marker als GeoJSON an die Karte."""
        if self._view is None:
            logger.warning("MapBridge.load_photos: kein QWebEngineView gesetzt")
            return
        payload = json.dumps([m.to_dict() for m in markers])
        # JSON wird doppelt gequotet — sicher für runJavaScript
        safe = payload.replace("\\", "\\\\").replace("`", "\\`")
        self._view.page().runJavaScript(f"window.loadPhotos(`{safe}`)")

    def fly_to(self, lat: float, lon: float, zoom: int = 12) -> None:
        """Karte auf Koordinaten zentrieren."""
        if self._view is None:
            return
        self._view.page().runJavaScript(
            f"window.mapFlyTo({lat}, {lon}, {zoom})"
        )

    def set_view(self, web_view: "QWebEngineView") -> None:
        self._view = web_view

    # ------------------------------------------------------------------
    # JavaScript → Python  (via QWebChannel @Slot)
    # ------------------------------------------------------------------

    @Slot(float, float, float, float)
    def on_viewport_changed(self, north: float, south: float,
                            east: float, west: float) -> None:
        """Wird von JS aufgerufen, wenn der Kartenausschnitt sich ändert."""
        self.viewport_changed.emit(north, south, east, west)

    @Slot(int)
    def on_marker_clicked(self, file_id: int) -> None:
        """Wird von JS aufgerufen, wenn ein Marker angeklickt wird."""
        self.marker_clicked.emit(file_id)

    @Slot(str)
    def on_map_ready(self, msg: str) -> None:
        """Wird von JS aufgerufen, sobald die Karte vollständig initialisiert ist."""
        logger.info("Karte bereit: %s", msg)
