"""Integration tests for all HTTP endpoints: pages, SEO, catalog, analytics, health, crypto, and security headers."""

import struct
import zlib

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_png(r=255, g=0, b=0):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    raw = b"\x00" + bytes([r, g, b])
    compressed = zlib.compress(raw)
    idat_crc = zlib.crc32(b"IDAT" + compressed)
    idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)
    iend_crc = zlib.crc32(b"IEND")
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
    return sig + ihdr + idat + iend


class TestPages:
    def test_homepage(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_tools_directory(self):
        resp = client.get("/tools")
        assert resp.status_code == 200

    def test_valid_tool_page(self):
        resp = client.get("/tool/qr-generator")
        assert resp.status_code == 200

    def test_invalid_tool_returns_404(self):
        resp = client.get("/tool/this-tool-does-not-exist")
        assert resp.status_code == 404

    def test_sitemap_page(self):
        resp = client.get("/sitemap")
        assert resp.status_code == 200

    def test_offline_page(self):
        resp = client.get("/offline")
        assert resp.status_code == 200

    def test_service_worker(self):
        resp = client.get("/sw.js")
        assert resp.status_code == 200


class TestSEORoutes:
    def test_sitemap_xml(self):
        resp = client.get("/sitemap.xml")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]
        assert "storybrainai.com" in resp.text

    def test_robots_txt(self):
        resp = client.get("/robots.txt")
        assert resp.status_code == 200
        assert "Sitemap" in resp.text

    def test_llms_txt(self):
        resp = client.get("/llms.txt")
        assert resp.status_code == 200
        assert "StoryBrain" in resp.text


class TestCatalogAPI:
    def test_tools_catalog(self):
        resp = client.get("/api/tools/catalog")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 10
        for tool in data:
            assert "name" in tool
            assert "url" in tool
            assert "desc" in tool
            assert "category" in tool

    def test_catalog_tool_has_url(self):
        resp = client.get("/api/tools/catalog")
        data = resp.json()
        for tool in data:
            assert tool["url"].startswith("/tool/")
            assert len(tool["name"]) > 0


class TestAnalyticsAPI:
    def test_track(self):
        resp = client.post("/api/track", json={"name": "test_tool", "category": "test"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_analytics_top(self):
        resp = client.get("/api/analytics/top")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)


class TestHealthEndpoints:
    def test_healthz(self):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_readyz(self):
        resp = client.get("/readyz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_metrics(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "http_requests_total" in resp.text


class TestCryptoAsync:
    def test_predict_crypto_async_returns_job_id(self):
        resp = client.get("/api/predict-crypto-async?symbol=BTC-USD")
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] in ("pending", "running")

    def test_analyze_crypto_trend_async_returns_job_id(self):
        resp = client.get("/api/analyze-crypto-trend-async?symbol=BTC-USD")
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] in ("pending", "running")

    def test_get_job_status_not_found(self):
        resp = client.get("/api/jobs/nonexistent-id")
        assert resp.status_code == 404


class TestSecurityHeaders:
    def test_hsts_header(self):
        resp = client.get("/")
        assert "strict-transport-security" in {k.lower(): v for k, v in resp.headers.items()}

    def test_xframe_options(self):
        resp = client.get("/")
        assert resp.headers.get("x-frame-options") == "DENY" or resp.headers.get("X-Frame-Options") == "DENY"

    def test_xcontent_type_options(self):
        resp = client.get("/")
        val = resp.headers.get("x-content-type-options") or resp.headers.get("X-Content-Type-Options")
        assert val == "nosniff"
