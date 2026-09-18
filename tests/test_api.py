"""Integration tests for all HTTP endpoints: pages, SEO, catalog, analytics, health, crypto, and security headers."""

import struct
import zlib

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 80))


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
        
    def test_directory_redirect(self):
        resp = client.get("/directory", follow_redirects=False)
        assert resp.status_code in (301, 302, 307, 308)
        assert "/tools" in resp.headers.get("location", "")

    def test_homepage_contains_all_tools(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert 'id="tools"' in resp.text
        assert 'id="toolSearchInput"' in resp.text
        assert 'id="toolsGrid"' in resp.text

    def test_qr_generator_returns_200(self):
        resp = client.get("/tool/qr-generator")
        assert resp.status_code == 200

    def test_css_filter_generator_returns_200(self):
        resp = client.get("/tool/css-filter-generator")
        assert resp.status_code == 200
        assert "cfgFilters" in resp.text
        assert "cfgPresets" in resp.text
        assert "cfgCssOutput" in resp.text
        assert "cfgPreviewBox" in resp.text
        assert "backdrop-filter" in resp.text
        assert "cfgDsEnable" in resp.text
        assert "cfgSaveLib" in resp.text
        assert "cfgCopyLink" in resp.text
        assert "cfgPlayBtn" in resp.text

    def test_css_animation_generator_returns_200(self):
        resp = client.get("/tool/css-animation-generator")
        assert resp.status_code == 200
        assert "cagTimelineTrack" in resp.text
        assert "cagPreviewBox" in resp.text
        assert "cagAnimStyle" in resp.text
        assert "cagCssOutput" in resp.text
        assert "cagPlayBtn" in resp.text
        assert "cagPropsContainer" in resp.text
        assert "cagPresets" in resp.text
        assert "cagBgBtns" in resp.text
        assert "cagCopyCss" in resp.text
        assert "cagTimingContainer" in resp.text

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
        # Must come from localhost (internal guard)
        resp = client.get("/api/analytics/top", headers={"X-Real-IP": "127.0.0.1"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_analytics_top_forbidden_from_external(self):
        resp = client.get("/api/analytics/top", headers={"X-Real-IP": "8.8.8.8"})
        assert resp.status_code == 403


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
        # Must come from localhost (internal guard)
        resp = client.get("/metrics", headers={"X-Real-IP": "127.0.0.1"})
        assert resp.status_code == 200
        assert "http_requests_total" in resp.text

    def test_metrics_forbidden_from_external(self):
        resp = client.get("/metrics", headers={"X-Real-IP": "8.8.8.8"})
        assert resp.status_code == 403


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


class TestNewRouteFeatures:
    def test_contact_submission(self):
        resp = client.post(
            "/api/contact",
            json={"name": "Alice", "email": "alice@example.com", "message": "Hello world"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_contact_submission_invalid(self):
        resp = client.post("/api/contact", json={"name": "", "email": "invalid", "message": ""})
        assert resp.status_code in (400, 422)

    def test_fng_invalid_limit(self):
        resp = client.get("/api/fng?limit=0")
        assert resp.status_code == 400
        resp2 = client.get("/api/fng?limit=999")
        assert resp2.status_code == 400

    def test_convert_to_pdf_invalid_type(self):
        resp = client.post(
            "/api/convert-to-pdf",
            files={"file": ("test.exe", b"binary content", "application/x-msdownload")},
        )
        assert resp.status_code == 400

    def test_convert_to_pdf_corrupt_image(self):
        resp = client.post(
            "/api/convert-to-pdf",
            files={"file": ("test.png", b"not-a-valid-image", "image/png")},
        )
        assert resp.status_code in (400, 422)

    def test_remove_background_unsupported_type(self):
        resp = client.post(
            "/api/remove-background",
            files={"image": ("test.txt", b"plain text", "text/plain")},
        )
        assert resp.status_code == 400

    def test_remove_watermark_invalid_algo(self):
        resp = client.post(
            "/api/remove-watermark",
            files={
                "image": ("img.png", _make_png(), "image/png"),
                "mask": ("mask.png", _make_png(), "image/png"),
            },
            data={"algorithm": "invalid_algo"},
        )
        assert resp.status_code == 400

    def test_nft_requires_key_for_external(self):
        resp = client.post(
            "/api/generate-nft",
            json={"prompt": "cyberpunk city", "provider": "openai"},
        )
        assert resp.status_code == 401

    def test_proxy_blocks_private_ip(self):
        resp = client.post(
            "/api/proxy-request",
            json={"url": "http://127.0.0.1:8000/secret", "method": "GET"},
        )
        assert resp.status_code in (400, 422)

    def test_empty_job_id(self):
        resp = client.get("/api/jobs/%20")
        assert resp.status_code in (400, 404)


class TestHeadersAndCaching:
    def test_favicon_cache_control(self):
        resp = client.get("/favicon.ico")
        if resp.status_code == 200:
            assert "cache-control" in {k.lower(): v for k, v in resp.headers.items()}
            assert "max-age" in resp.headers.get("cache-control", "").lower()

    def test_ads_txt_cache_control(self):
        resp = client.get("/ads.txt")
        if resp.status_code == 200:
            assert "cache-control" in {k.lower(): v for k, v in resp.headers.items()}
            assert "max-age" in resp.headers.get("cache-control", "").lower()

    def test_static_sw_cache_control(self):
        resp = client.get("/static/sw.js")
        if resp.status_code == 200:
            cc = resp.headers.get("cache-control", "")
            assert "no-store" in cc or "no-cache" in cc

    def test_cors_expose_headers(self):
        resp = client.options(
            "/api/tools/catalog",
            headers={
                "Origin": "http://localhost:8090",
                "Access-Control-Request-Method": "GET",
            },
        )
        exposed = resp.headers.get("access-control-expose-headers", "")
        # Either preflight or simple request with Origin should expose X-Request-ID
        simple_resp = client.get(
            "/api/tools/catalog",
            headers={"Origin": "http://localhost:8090"},
        )
        assert "x-request-id" in simple_resp.headers.get("access-control-expose-headers", "").lower()

