#!/usr/bin/env python3
"""SlopOS Website Server - serves static files + proxies map tiles."""
import http.server
import os
import sys
import urllib.request
import urllib.parse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

class SiteHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Prevent caching on HTML to avoid stale page content
        if self.path == '/' or self.path.endswith('.html'):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        # Tile proxy: /api/tile?z={z}&x={x}&y={y}
        if self.path.startswith("/api/tile?"):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            try:
                z = params["z"][0]
                x = params["x"][0]
                y = params["y"][0]
            except (KeyError, IndexError):
                self.send_error(400, "Missing z, x, y params")
                return
            tile_url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            # Dark tiles from CartoDB
            if params.get("style", [None])[0] == "dark":
                sub = "a" if (int(x) + int(y)) % 2 == 0 else "b"
                tile_url = f"https://{sub}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
            req = urllib.request.Request(tile_url, headers={
                "User-Agent": "SlopOSMapTool/1.0",
            })
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_error(502, f"Tile proxy error: {e}")
            return

        return super().do_GET()

    def log_message(self, fmt, *args):
        print(f"[site] {args[0]} {args[1]} {args[2]}")

if __name__ == "__main__":
    http.server.HTTPServer.allow_reuse_address = True
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"Serving site on http://0.0.0.0:{PORT} (static + tile proxy)")
    http.server.HTTPServer(("0.0.0.0", PORT), SiteHandler).serve_forever()
