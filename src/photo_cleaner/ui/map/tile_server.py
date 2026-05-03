"""Lokaler HTTP-Server für Karten-Assets und gecachte OSM-Tiles.

Architektur:
  GET /tiles/{z}/{x}/{y}.png  → aus TileCache (SQLite MBTiles)
  GET /map.html, /*.js, /*.css → statische Assets aus assets_dir

Ausschließlich auf 127.0.0.1 gebunden — kein Netzwerkzugriff von außen.
"""
from __future__ import annotations

import logging
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from photo_cleaner.ui.map.tile_cache import TileCache

logger = logging.getLogger(__name__)

# Globale Referenz auf den Cache — wird von TileServer gesetzt
_tile_cache: "TileCache | None" = None
_assets_dir: Path = Path(".")


class _MapHandler(BaseHTTPRequestHandler):
    """HTTP-Handler: Tile-Cache-Anfragen + statische Assets."""

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        pass

    def log_error(self, fmt: str, *args) -> None:  # type: ignore[override]
        logger.warning("TileServer: " + fmt % args)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]  # Query-String entfernen

        # ── Tile-Anfragen: /tiles/{z}/{x}/{y}.png ──────────────────────
        if path.startswith("/tiles/"):
            self._serve_tile(path)
            return

        # ── Statische Assets ───────────────────────────────────────────
        self._serve_static(path)

    def _serve_tile(self, path: str) -> None:
        """Bedient Tile aus lokalem Cache. 404 wenn nicht gecacht."""
        try:
            parts = path.strip("/").split("/")  # ["tiles", z, x, "y.png"]
            z = int(parts[1])
            x = int(parts[2])
            y = int(parts[3].replace(".png", ""))
        except (IndexError, ValueError):
            self._send(400, b"Bad tile path", "text/plain")
            return

        if _tile_cache is not None:
            data = _tile_cache.get(z, x, y)
        else:
            data = None

        if data is None:
            self._send(404, b"Tile not cached", "text/plain")
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, path: str) -> None:
        """Bedient statische Dateien aus dem Assets-Verzeichnis."""
        if path in ("/", ""):
            path = "/map.html"

        file_path = _assets_dir / path.lstrip("/")

        # Path-Traversal verhindern
        try:
            file_path.resolve().relative_to(_assets_dir.resolve())
        except ValueError:
            self._send(403, b"Forbidden", "text/plain")
            return

        if not file_path.is_file():
            self._send(404, b"Not Found", "text/plain")
            return

        ext = file_path.suffix.lower()
        mime = {
            ".html": "text/html; charset=utf-8",
            ".js":   "application/javascript",
            ".css":  "text/css",
            ".png":  "image/png",
            ".json": "application/json",
        }.get(ext, "application/octet-stream")

        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class TileServer(threading.Thread):
    """HTTP-Server der Tile-Cache + statische Assets ausliefert.

    Parameters
    ----------
    assets_dir:
        Verzeichnis mit map.html, maplibre-gl.js, maplibre-gl.css, pmtiles.js
    cache:
        TileCache-Instanz (kann None sein — dann werden nur Assets geliefert)
    port:
        TCP-Port (Standard 0 → automatisch freier Port)
    """

    def __init__(
        self,
        assets_dir: str | Path,
        cache: "TileCache | None" = None,
        port: int = 0,
    ) -> None:
        super().__init__(daemon=True, name="PhotoCleaner-TileServer")
        self.assets_dir = Path(assets_dir)
        self._cache = cache
        self._requested_port = port
        self._server: HTTPServer | None = None
        self._ready = threading.Event()

    @property
    def port(self) -> int:
        self._ready.wait(timeout=5)
        assert self._server is not None, "TileServer nicht gestartet"
        return self._server.server_address[1]

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()

    def run(self) -> None:
        global _tile_cache, _assets_dir
        _tile_cache = self._cache
        _assets_dir = self.assets_dir
        try:
            self._server = HTTPServer(("127.0.0.1", self._requested_port), _MapHandler)
            self._ready.set()
            bound_port = self._server.server_address[1]
            logger.info(
                "TileServer gestartet auf http://127.0.0.1:%d (Assets: %s, Cache: %s)",
                bound_port,
                self.assets_dir,
                "ja" if self._cache else "nein",
            )
            self._server.serve_forever()
        except Exception:
            logger.exception("TileServer-Fehler")
            self._ready.set()


def find_free_port() -> int:
    """Gibt einen freien TCP-Port zurück."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
