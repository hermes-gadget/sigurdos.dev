#!/usr/bin/env python3
"""SigurdOS Website Server - serves approved public files + proxies map tiles."""
import http.server
import mimetypes
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
REPOSITORY_ROOT = Path(__file__).resolve().parent
PUBLIC_ROOT = REPOSITORY_ROOT / "public"
PUBLIC_FILES = {
    "/": PUBLIC_ROOT / "index.html",
    "/index.html": PUBLIC_ROOT / "index.html",
    "/site.js": PUBLIC_ROOT / "site.js",
    "/img/chat.png": PUBLIC_ROOT / "img/chat.png",
    "/img/map.png": PUBLIC_ROOT / "img/map.png",
    "/img/contacts.png": PUBLIC_ROOT / "img/contacts.png",
    "/img/repeaters.png": PUBLIC_ROOT / "img/repeaters.png",
    "/img/channels.png": PUBLIC_ROOT / "img/channels.png",
    "/img/network.png": PUBLIC_ROOT / "img/network.png",
    "/img/signal.png": PUBLIC_ROOT / "img/signal.png",
    "/img/sigurdos-banner.png": PUBLIC_ROOT / "img/sigurdos-banner.png",
    "/img/home.png": PUBLIC_ROOT / "img/home.png",
    "/img/terminal.png": PUBLIC_ROOT / "img/terminal.png",
}

CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'self'",
        "connect-src 'self' https://api.github.com https://tile.openstreetmap.org "
        "https://*.basemaps.cartocdn.com",
        "font-src https://fonts.gstatic.com",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "img-src 'self' data: https://avatars.githubusercontent.com https://unpkg.com "
        "https://tile.openstreetmap.org https://*.basemaps.cartocdn.com",
        "object-src 'none'",
        "script-src 'self' "
        "'sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com",
    )
)

class SiteHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Permissions-Policy",
            "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
        )
        # Prevent caching on HTML to avoid stale page content
        request_path = urllib.parse.urlsplit(self.path).path
        if request_path == "/" or request_path.endswith(".html"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        # Tile proxy: /api/tile?z={z}&x={x}&y={y}
        request = urllib.parse.urlsplit(self.path)
        if request.path == "/api/tile":
            params = urllib.parse.parse_qs(request.query)
            try:
                z = int(params["z"][0])
                x = int(params["x"][0])
                y = int(params["y"][0])
            except (KeyError, IndexError, ValueError):
                self.send_error(400, "Invalid z, x, y params")
                return
            tile_limit = 1 << z if 0 <= z <= 18 else 0
            if tile_limit == 0 or not (0 <= x < tile_limit and 0 <= y < tile_limit):
                self.send_error(400, "Tile coordinates out of range")
                return
            tile_url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            # Dark tiles from CartoDB
            if params.get("style", [None])[0] == "dark":
                sub = "a" if (x + y) % 2 == 0 else "b"
                tile_url = f"https://{sub}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
            req = urllib.request.Request(tile_url, headers={
                "User-Agent": "SigurdOSMapTool/1.1 (+https://www.sigurdos.dev)",
                "Referer": "https://www.sigurdos.dev/",
            })
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    cache_headers = ("Cache-Control", "Expires", "ETag", "Last-Modified")
                    if not any(resp.headers.get(name) for name in cache_headers[:2]):
                        self.send_header("Cache-Control", "public, max-age=604800")
                    for name in cache_headers:
                        if value := resp.headers.get(name):
                            self.send_header(name, value)
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_error(502, f"Tile proxy error: {e}")
            return

        self._serve_public_file(request.path, send_body=True)

    def do_HEAD(self):
        request_path = urllib.parse.urlsplit(self.path).path
        self._serve_public_file(request_path, send_body=False)

    def _serve_public_file(self, request_path, *, send_body):
        """Serve only the exact files listed in PUBLIC_FILES."""
        try:
            decoded_path = urllib.parse.unquote(request_path, errors="strict")
        except UnicodeDecodeError:
            self.send_error(404)
            return

        file_path = PUBLIC_FILES.get(decoded_path)
        if file_path is None:
            self.send_error(404)
            return

        try:
            source = file_path.open("rb")
        except OSError:
            self.send_error(404)
            return

        with source:
            stat = os.fstat(source.fileno())
            content_type = mimetypes.guess_type(file_path.name)[0]
            self.send_response(200)
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(stat.st_size))
            self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
            self.end_headers()
            if send_body:
                self.copyfile(source, self.wfile)

    def log_message(self, fmt, *args):
        print(f"[site] {self.address_string()} - {fmt % args}")

if __name__ == "__main__":
    http.server.HTTPServer.allow_reuse_address = True
    print(f"Serving site on http://0.0.0.0:{PORT} (allowlisted static files + tile proxy)")
    http.server.HTTPServer(("0.0.0.0", PORT), SiteHandler).serve_forever()
