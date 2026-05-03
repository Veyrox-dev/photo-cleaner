"""MapWidget — PySide6-Widget für die Offline-Fotokarte.

Beinhaltet:
- QWebEngineView mit MapLibre GL JS (Raster-Tiles aus lokalem Cache)
- QWebChannel für bidirektionale Kommunikation
- Lokalen TileServer (Daemon-Thread, bedient /tiles/{z}/{x}/{y}.png aus Cache)
- Automatischer Tile-Download beim ersten Start (nur Regionen mit Fotos)
- DB-Abfrage: Fotos mit GPS-Koordinaten aus geo_groups/geo_group_images/files
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from photo_cleaner.ui.map.map_bridge import MapBridge, PhotoMarker
from photo_cleaner.ui.map.tile_cache import TileCache, DEFAULT_CACHE_PATH
from photo_cleaner.ui.map.tile_downloader import BoundingBox, TileDownloadWorker
from photo_cleaner.ui.map.tile_server import TileServer

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).parent / "assets"
MAX_ZOOM_DOWNLOAD = 14


class MapWidget(QWidget):
    """Vollbild-Karten-Widget für die Foto-Standort-Visualisierung.

    Signals
    -------
    viewport_changed(north, south, east, west):
        Weitergeleitet von MapBridge — wird von GalleryView genutzt
        um sichtbare Fotos zu filtern.
    marker_clicked(file_id):
        Nutzer hat einen Foto-Marker auf der Karte angeklickt.
    close_requested:
        "×"-Button oben links wurde gedrückt.
    """

    viewport_changed = Signal(float, float, float, float)
    marker_clicked = Signal(int)
    close_requested = Signal()

    def __init__(self, db_path: str | Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._server: Optional[TileServer] = None
        self._cache: Optional[TileCache] = None
        self._bridge = MapBridge(self)
        self._channel = QWebChannel(self)
        self._loaded = False
        self._download_worker: Optional[TileDownloadWorker] = None

        self._build_ui()
        self._connect_signals()
        self._start_server()

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(40)
        toolbar.setStyleSheet(
            "background: #1e1e1e; border-bottom: 1px solid #333;"
        )
        tbl = QHBoxLayout(toolbar)
        tbl.setContentsMargins(8, 0, 8, 0)

        close_btn = QPushButton("← Zurück zur Galerie")
        close_btn.setFlat(True)
        close_btn.setStyleSheet(
            "color: #ccc; font-size: 13px; padding: 4px 10px;"
            "border: none; background: transparent;"
        )
        close_btn.clicked.connect(self.close_requested)
        tbl.addWidget(close_btn)

        tbl.addStretch()

        self._status_label = QLabel("Karte wird geladen …")
        self._status_label.setStyleSheet("color: #888; font-size: 12px;")
        tbl.addWidget(self._status_label)

        root.addWidget(toolbar)

        # ── WebView ───────────────────────────────────────────────────
        self._view = QWebEngineView()
        self._view.page().setWebChannel(self._channel)
        root.addWidget(self._view)

        self._bridge.set_view(self._view)
        self._channel.registerObject("mapBridge", self._bridge)

        self._loading_overlay = QWidget(self)
        self._loading_overlay.setStyleSheet("background: rgba(9, 12, 18, 0.82);")
        self._loading_overlay.hide()

        overlay_layout = QVBoxLayout(self._loading_overlay)
        overlay_layout.setContentsMargins(24, 24, 24, 24)
        overlay_layout.addStretch(1)

        panel = QFrame()
        panel.setMaximumWidth(520)
        panel.setStyleSheet(
            "QFrame {"
            "background: #171b22;"
            "border: 1px solid #2e3846;"
            "border-radius: 14px;"
            "}"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 22, 24, 20)
        panel_layout.setSpacing(10)

        self._overlay_title = QLabel("Karte wird vorbereitet")
        self._overlay_title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        panel_layout.addWidget(self._overlay_title)

        self._overlay_message = QLabel("Pruefe lokalen Karten-Cache ...")
        self._overlay_message.setWordWrap(True)
        self._overlay_message.setStyleSheet("color: #cbd5e1; font-size: 13px;")
        panel_layout.addWidget(self._overlay_message)

        self._overlay_progress = QProgressBar()
        self._overlay_progress.setRange(0, 0)
        self._overlay_progress.setTextVisible(True)
        self._overlay_progress.setStyleSheet(
            "QProgressBar {"
            "background: #0f1318; color: #f8fafc; border: 1px solid #3a4555;"
            "border-radius: 7px; text-align: center; min-height: 20px;"
            "}"
            "QProgressBar::chunk { background: #3b82f6; border-radius: 6px; }"
        )
        panel_layout.addWidget(self._overlay_progress)

        self._overlay_detail = QLabel("")
        self._overlay_detail.setStyleSheet("color: #94a3b8; font-size: 12px;")
        panel_layout.addWidget(self._overlay_detail)

        self._overlay_cancel_btn = QPushButton("Download abbrechen")
        self._overlay_cancel_btn.hide()
        self._overlay_cancel_btn.clicked.connect(self._cancel_download)
        panel_layout.addWidget(self._overlay_cancel_btn, alignment=Qt.AlignRight)

        # Confirm-Leiste für "Jetzt herunterladen?" (nicht-blockierend)
        self._confirm_bar = QWidget()
        confirm_layout = QHBoxLayout(self._confirm_bar)
        confirm_layout.setContentsMargins(0, 4, 0, 0)
        self._confirm_download_btn = QPushButton("Jetzt herunterladen")
        self._confirm_download_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; color: #fff; border: none;"
            "border-radius: 6px; padding: 6px 18px; font-size: 13px; }"
            "QPushButton:hover { background: #2563eb; }"
        )
        self._confirm_skip_btn = QPushButton("Überspringen")
        self._confirm_skip_btn.setStyleSheet(
            "QPushButton { background: #374151; color: #cbd5e1; border: none;"
            "border-radius: 6px; padding: 6px 18px; font-size: 13px; }"
            "QPushButton:hover { background: #4b5563; }"
        )
        confirm_layout.addStretch()
        confirm_layout.addWidget(self._confirm_download_btn)
        confirm_layout.addWidget(self._confirm_skip_btn)
        self._confirm_bar.hide()
        panel_layout.addWidget(self._confirm_bar)

        overlay_layout.addWidget(panel, alignment=Qt.AlignCenter)
        overlay_layout.addStretch(1)

        self._update_loading_overlay_geometry()

    def _connect_signals(self) -> None:
        self._bridge.viewport_changed.connect(self.viewport_changed)
        self._bridge.marker_clicked.connect(self.marker_clicked)
        self._view.loadFinished.connect(self._on_load_finished)

    # ------------------------------------------------------------------
    # Tile-Server
    # ------------------------------------------------------------------

    def _start_server(self) -> None:
        if not _ASSETS_DIR.exists():
            logger.warning("Map-Assets-Verzeichnis fehlt: %s", _ASSETS_DIR)
            self._status_label.setText("Karten-Assets fehlen.")
            return
        self._show_loading_overlay(
            title="Karte wird vorbereitet",
            message="Starte lokalen Kartenserver und pruefe den Cache ...",
            determinate=False,
        )
        self._cache = TileCache(DEFAULT_CACHE_PATH)
        self._server = TileServer(_ASSETS_DIR, cache=self._cache, port=0)
        self._server.start()
        QTimer.singleShot(300, self._check_cache_then_load)

    # ------------------------------------------------------------------
    # Cache-Prüfung + Download-Dialog
    # ------------------------------------------------------------------

    def _check_cache_then_load(self) -> None:
        """Prüft ob Tiles vorhanden sind. Falls nicht → Download anbieten."""
        if self._cache is None:
            logger.info("[Map] Kein TileCache verfuegbar, lade Karte ohne Offline-Hintergrund")
            self._load_map()
            return

        cached_count = self._cache.count()
        logger.info(
            "[Map] Cache-Pruefung abgeschlossen: %d Tiles, %.1f MB",
            cached_count,
            self._cache.size_mb(),
        )
        if cached_count > 0:
            self._show_loading_overlay(
                title="Offline-Karte wird geladen",
                message="Lokaler Karten-Cache wurde gefunden. Basiskarte wird geladen ...",
                detail=f"{cached_count} Tiles im Cache ({self._cache.size_mb():.1f} MB)",
                determinate=False,
            )
            self._status_label.setText(
                f"Karte aus Cache ({self._cache.size_mb():.0f} MB)"
            )
            self._load_map()
            return

        self._show_loading_overlay(
            title="Offline-Kartenmaterial fehlt",
            message="Es wurde noch kein Karten-Cache gefunden.",
            detail="Vor dem ersten Einsatz muessen Kartendaten fuer deine Foto-Regionen geladen werden.",
            determinate=False,
        )

        coords = self._load_gps_coords_from_db()
        bbox = BoundingBox.from_points(coords)
        est_mb = bbox.size_estimate_mb(MAX_ZOOM_DOWNLOAD)
        tile_count = bbox.tile_count(MAX_ZOOM_DOWNLOAD)
        logger.info(
            "[Map] Cache leer, vorgeschlagener Download: %d Tiles (~%.1f MB) fuer Bounding Box S=%.4f W=%.4f N=%.4f E=%.4f",
            tile_count,
            est_mb,
            bbox.south,
            bbox.west,
            bbox.north,
            bbox.east,
        )

        detail_text = (
            f"Bereich: {bbox.south:.1f}° – {bbox.north:.1f}°N · "
            f"{bbox.west:.1f}° – {bbox.east:.1f}°E\n"
            f"Geschätzte Größe: ~{est_mb:.0f} MB ({tile_count} Tiles)  ·  Einmalig, danach offline verfügbar."
        )
        self._show_loading_overlay(
            title="Kartenmaterial herunterladen?",
            message="Es wurden noch keine Karten-Tiles heruntergeladen.",
            detail=detail_text,
            determinate=False,
        )
        # Overlay-Fortschrittsbalken ausblenden während Bestätigung wartet
        self._overlay_progress.hide()
        self._confirm_bar.show()

        # Einmalig verbinden (lambdas mit capture, um bbox weiterzugeben)
        def _do_download() -> None:
            self._confirm_bar.hide()
            self._overlay_progress.show()
            self._confirm_download_btn.clicked.disconnect()
            self._confirm_skip_btn.clicked.disconnect()
            self._start_download(bbox)

        def _do_skip() -> None:
            self._confirm_bar.hide()
            self._overlay_progress.show()
            self._confirm_download_btn.clicked.disconnect()
            self._confirm_skip_btn.clicked.disconnect()
            logger.info("[Map] Nutzer hat den initialen Tile-Download abgelehnt")
            self._status_label.setText(
                "Keine Karten-Tiles — Karte zeigt nur Marker ohne Hintergrund."
            )
            self._load_map()

        self._confirm_download_btn.clicked.connect(_do_download)
        self._confirm_skip_btn.clicked.connect(_do_skip)

    def _start_download(self, bbox: BoundingBox) -> None:
        """Startet den Tile-Download im Hintergrund mit sichtbarem Ladescreen."""
        assert self._cache is not None
        logger.info("[Map] Starte Tile-Download bis Zoom %d", MAX_ZOOM_DOWNLOAD)
        self._show_loading_overlay(
            title="Kartendaten werden heruntergeladen",
            message="Verbinde mit OpenStreetMap und lade nur die benoetigten Bereiche ...",
            detail="Der Download laeuft im Hintergrund. Danach ist die Karte offline verfuegbar.",
            determinate=True,
            current=0,
            total=max(1, bbox.tile_count(MAX_ZOOM_DOWNLOAD)),
            cancelable=True,
        )

        self._download_worker = TileDownloadWorker(bbox, self._cache, MAX_ZOOM_DOWNLOAD, self)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.status_message.connect(self._on_download_status)
        self._download_worker.finished_ok.connect(self._on_download_finished)
        self._download_worker.error_occurred.connect(self._on_download_error)
        self._download_worker.start()

    # ------------------------------------------------------------------
    # Karte laden
    # ------------------------------------------------------------------

    def _load_map(self) -> None:
        if self._server is None:
            return
        port = self._server.port
        # port als Query-Parameter damit map.html den TileServer-Port kennt
        map_url = f"http://127.0.0.1:{port}/map.html?port={port}"
        logger.info("Lade Karte von %s", map_url)
        self._view.load(QUrl(map_url))

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            self._status_label.setText("Fehler beim Laden der Karte.")
            logger.error("QWebEngineView: map.html konnte nicht geladen werden")
            self._hide_loading_overlay()
            return
        self._loaded = True
        self._status_label.setText("")
        self._hide_loading_overlay()
        # Fotos aus DB laden und als Marker übergeben
        QTimer.singleShot(500, self._push_markers)

    def _show_loading_overlay(
        self,
        title: str,
        message: str,
        detail: str = "",
        determinate: bool = False,
        current: int = 0,
        total: int = 0,
        cancelable: bool = False,
    ) -> None:
        self._overlay_title.setText(title)
        self._overlay_message.setText(message)
        self._overlay_detail.setText(detail)
        if determinate:
            self._overlay_progress.setRange(0, max(1, total))
            self._overlay_progress.setValue(min(current, max(1, total)))
            self._overlay_progress.setFormat("%v / %m Tiles")
        else:
            self._overlay_progress.setRange(0, 0)
            self._overlay_progress.setFormat("Lade ...")
        self._overlay_cancel_btn.setVisible(cancelable)
        self._overlay_progress.show()
        self._confirm_bar.hide()
        self._update_loading_overlay_geometry()
        self._loading_overlay.show()
        self._loading_overlay.raise_()

    def _hide_loading_overlay(self) -> None:
        self._loading_overlay.hide()

    def _update_loading_overlay_geometry(self) -> None:
        toolbar_height = 40
        self._loading_overlay.setGeometry(0, toolbar_height, self.width(), max(0, self.height() - toolbar_height))

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_loading_overlay_geometry()

    def _on_download_status(self, message: str) -> None:
        self._overlay_message.setText(message)
        self._status_label.setText(message)

    def _on_download_progress(self, done: int, total: int) -> None:
        self._overlay_progress.setRange(0, max(1, total))
        self._overlay_progress.setValue(done)
        self._overlay_detail.setText(
            f"{done} / {total} Tiles heruntergeladen · Cache: {self._cache.size_mb():.1f} MB"
        )

    def _on_download_finished(self, count: int) -> None:
        logger.info("[Map] Tile-Download abgeschlossen: %d neue Tiles", count)
        self._status_label.setText(f"Kartencache aktualisiert ({self._cache.size_mb():.1f} MB)")
        self._show_loading_overlay(
            title="Offline-Karte wird geladen",
            message="Download abgeschlossen. Die Karte wird jetzt aufgebaut ...",
            detail=f"Neu geladen: {count} Tiles · Cache: {self._cache.size_mb():.1f} MB",
            determinate=False,
        )
        self._load_map()

    def _on_download_error(self, message: str) -> None:
        logger.error("[Map] Tile-Download fehlgeschlagen: %s", message)
        self._show_loading_overlay(
            title="Download fehlgeschlagen",
            message=message,
            detail="Die Karte wird ohne Offline-Hintergrund geladen.",
            determinate=False,
        )
        QTimer.singleShot(2000, self._load_map)

    def _cancel_download(self) -> None:
        if self._download_worker is not None and self._download_worker.isRunning():
            logger.info("[Map] Nutzer bricht Tile-Download ab")
            self._download_worker.cancel()
            self._overlay_message.setText("Download wird abgebrochen ...")
            self._overlay_cancel_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Daten aus DB → Karte
    # ------------------------------------------------------------------

    def _push_markers(self) -> None:
        markers = self._load_markers_from_db()
        if not markers:
            self._status_label.setText(
                "Keine Fotos mit GPS-Koordinaten gefunden."
            )
            return
        self._status_label.setText(f"{len(markers)} Foto-Standorte geladen")
        self._bridge.load_photos(markers)

    def _load_gps_coords_from_db(self) -> list[tuple[float, float]]:
        """Liest alle GPS-Koordinaten aus geo_groups zurück."""
        coords: list[tuple[float, float]] = []
        if not self._db_path.exists():
            return coords
        try:
            with sqlite3.connect(str(self._db_path), check_same_thread=False) as con:
                cur = con.execute(
                    "SELECT latitude, longitude FROM geo_groups "
                    "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
                )
                coords = [(row[0], row[1]) for row in cur.fetchall()]
        except Exception:
            logger.exception("Fehler beim Lesen der GPS-Koordinaten")
        return coords

    def _load_markers_from_db(self) -> list[PhotoMarker]:
        """Liest Fotos mit GPS-Koordinaten aus der DB.

        JOIN: files ↔ geo_group_images ↔ geo_groups
        Nur Einträge mit gültiger latitude/longitude werden zurückgegeben.
        """
        markers: list[PhotoMarker] = []
        if not self._db_path.exists():
            return markers
        try:
            with sqlite3.connect(str(self._db_path), check_same_thread=False) as con:
                con.row_factory = sqlite3.Row
                cur = con.execute(
                    """
                    SELECT
                        f.file_id,
                        f.path,
                        f.quality_score,
                        f.exif_location_name,
                        gg.latitude,
                        gg.longitude
                    FROM files f
                    JOIN geo_group_images ggi ON ggi.file_id = f.file_id
                    JOIN geo_groups gg ON gg.id = ggi.geo_group_id
                    WHERE gg.latitude IS NOT NULL
                      AND gg.longitude IS NOT NULL
                      AND f.status = 'KEEP'
                    ORDER BY f.quality_score DESC
                    """
                )
                for row in cur.fetchall():
                    markers.append(
                        PhotoMarker(
                            file_id=row["file_id"],
                            lat=row["latitude"],
                            lon=row["longitude"],
                            path=row["path"],
                            score=row["quality_score"],
                            location_name=row["exif_location_name"],
                        )
                    )
        except Exception:
            logger.exception("Fehler beim Laden der Karten-Marker aus DB")
        return markers

    # ------------------------------------------------------------------
    # Öffentliche Steuerung
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Marker neu laden (z. B. nach Indexierung)."""
        if self._loaded:
            self._push_markers()

    def fly_to(self, lat: float, lon: float, zoom: int = 14) -> None:
        self._bridge.fly_to(lat, lon, zoom)

    def shutdown(self) -> None:
        """TileServer und Cache sauber beenden (bei App-Close aufrufen)."""
        if self._download_worker is not None and self._download_worker.isRunning():
            self._download_worker.cancel()
            self._download_worker.wait(3000)
        if self._server:
            self._server.stop()
        if self._cache:
            self._cache.close()
