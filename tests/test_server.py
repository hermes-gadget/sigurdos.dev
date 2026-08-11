"""Regression tests for the public HTTP boundary."""

from __future__ import annotations

import contextlib
import http.client
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class SiteServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with contextlib.closing(socket.socket()) as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]

        cls.server = subprocess.Popen(
            [sys.executable, str(REPOSITORY_ROOT / "server.py"), str(cls.port)],
            cwd=REPOSITORY_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if cls.server.poll() is not None:
                stderr = cls.server.stderr.read() if cls.server.stderr else ""
                raise RuntimeError(f"test server exited early: {stderr}")
            try:
                status, _, _ = cls.request("/")
                if status == 200:
                    return
            except OSError:
                time.sleep(0.05)
        cls.server.terminate()
        raise RuntimeError("test server did not become ready")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait(timeout=5)

    @classmethod
    def request(
        cls,
        path: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes, dict[str, str]]:
        connection = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            headers = {name.lower(): value for name, value in response.getheaders()}
            return response.status, response.read(), headers
        finally:
            connection.close()

    def test_only_explicitly_public_files_are_served(self) -> None:
        for path in (
            "/.git/config",
            "/.git",
            "/server.py",
            "/README.md",
            "/LICENSE",
            "/THIRD_PARTY_NOTICES.md",
            "/.env",
            "/sync_firmware.py",
            "/tests/test_server.py",
            "/assets/",
            "/img/",
            "/public/",
            "/public/index.html",
            "/%2eenv",
            "/%73erver.py",
            "/img/../server.py",
            "/index.html/..%2fserver.py",
        ):
            with self.subTest(path=path):
                status, _, _ = self.request(path)
                self.assertIn(status, (403, 404))

    def test_head_cannot_probe_private_files(self) -> None:
        status, _, _ = self.request("/server.py", method="HEAD")
        self.assertIn(status, (403, 404))

    def test_homepage_and_approved_asset_are_served(self) -> None:
        status, body, _ = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!doctype html>", body)

        status, body, headers = self.request("/img/home.png")
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(headers["content-type"], "image/png")

        status, body, headers = self.request("/site.js")
        self.assertEqual(status, 200)
        self.assertIn(b"'use strict';", body)
        self.assertIn("javascript", headers["content-type"])

        for path in ("/favicon.svg", "/favicon.ico", "/robots.txt", "/sitemap.xml"):
            with self.subTest(path=path):
                status, _, _ = self.request(path)
                self.assertEqual(status, 200)

    def test_legacy_host_redirects_to_canonical_host(self) -> None:
        status, body, headers = self.request(
            "/?source=legacy",
            headers={"Host": "sigurdos.dev"},
        )
        self.assertEqual(status, 301)
        self.assertEqual(headers["location"], "https://www.sigurdos.dev/?source=legacy")
        self.assertEqual(body, b"")

    def test_tile_api_route_is_preserved(self) -> None:
        status, _, _ = self.request("/api/tile?z=1")
        self.assertEqual(status, 400)
        status, _, _ = self.request("/api/tile?z=19&x=0&y=0")
        self.assertEqual(status, 400)
        status, _, _ = self.request("/api/tile?z=1&x=2&y=0&style=dark")
        self.assertEqual(status, 400)

    def test_security_headers_and_sri_are_present(self) -> None:
        status, body, headers = self.request("/")
        self.assertEqual(status, 200)
        policy = headers["content-security-policy"]
        self.assertIn("default-src 'self'", policy)
        self.assertIn(
            "script-src 'self' "
            "'sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH'",
            policy,
        )
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertNotIn("script-src 'unsafe-inline'", policy)
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(headers["referrer-policy"], "strict-origin-when-cross-origin")
        self.assertIn("permissions-policy", headers)
        self.assertNotIn(b"<script>", body)
        self.assertNotIn(b"onclick=", body)
        self.assertIn(
            b'integrity="sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH"',
            body,
        )
        self.assertIn(
            b'integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H"',
            body,
        )

    def test_page_has_no_osm_offline_prefetcher(self) -> None:
        _, page, _ = self.request("/")
        _, javascript, _ = self.request("/site.js")
        self.assertNotIn(b"JSZip", page + javascript)
        self.assertNotIn(b"tile-download-btn", page + javascript)
        self.assertNotIn(b"/api/tile", javascript)
        self.assertIn(b"attributionControl: true", javascript)
        self.assertIn(b"maxBounds: worldBounds", javascript)
        self.assertIn(b"noWrap: true", javascript)

    def test_release_and_security_copy_are_current(self) -> None:
        _, body, _ = self.request("/")
        normalized_body = b" ".join(body.split())
        self.assertIn(b"beta-0.1.47-RC9", body)
        self.assertIn(b"1,587", body)
        self.assertIn(b"as of August 11, 2026", body)
        self.assertNotIn(b"SlopOS", body)
        self.assertNotIn(b"beta-0.1.44 RC6", body)
        self.assertNotIn(b"Every packet is encrypted with Ed25519", normalized_body)
        self.assertIn(b"Ed25519 authenticates identities and signatures", normalized_body)
        self.assertIn(b"Group messages use a shared channel key", normalized_body)
        self.assertIn(b"do not authenticate an individual sender", normalized_body)
        self.assertIn(b"not every packet is encrypted", normalized_body)
        self.assertIn(b"tiles/&lt;z&gt;/&lt;x&gt;/&lt;y&gt;.png", normalized_body)
        self.assertNotIn(b".jpg", normalized_body)
        _, javascript, _ = self.request("/site.js")
        self.assertNotIn(b"innerHTML", javascript)


if __name__ == "__main__":
    unittest.main()
