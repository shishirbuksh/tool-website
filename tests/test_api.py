import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


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


class TestBase64API:
    def test_encode(self):
        resp = client.post("/api/base64-encode", data={"text": "hello"})
        assert resp.status_code == 200
        assert resp.json()["result"] == "aGVsbG8="

    def test_decode(self):
        resp = client.post("/api/base64-decode", data={"text": "aGVsbG8="})
        assert resp.status_code == 200
        assert resp.json()["result"] == "hello"

    def test_decode_invalid_returns_422(self):
        resp = client.post("/api/base64-decode", data={"text": "not-valid!!!val"})
        assert resp.status_code == 422
        assert resp.json()["detail"] == "Invalid Base64 string"


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


class TestPing:
    def test_ping(self):
        resp = client.get("/api/ping")
        assert resp.status_code == 200
        assert resp.json() == {"ping": "pong"}


class TestQRIntegration:
    def test_generate_qr_returns_png(self):
        resp = client.post("/api/generate-qr", data={"data": "https://example.com"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_generate_qr_with_colors(self):
        resp = client.post("/api/generate-qr", data={
            "data": "hello", "fg_color": "red", "bg_color": "white",
        })
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"


class TestPDFIntegration:
    def test_convert_text_to_pdf(self):
        resp = client.post(
            "/api/convert-to-pdf",
            files={"file": ("test.txt", b"Hello World", "text/plain")},
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]

    def test_convert_text_to_pdf_multiline(self):
        resp = client.post(
            "/api/convert-to-pdf",
            files={"file": ("test.txt", b"Line1\nLine2\nLine3", "text/plain")},
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]

    def test_convert_text_to_pdf_empty(self):
        resp = client.post(
            "/api/convert-to-pdf",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]

    def test_convert_to_pdf_unsupported_format(self):
        resp = client.post(
            "/api/convert-to-pdf",
            files={"file": ("test.exe", b"nope", "application/octet-stream")},
        )
        assert resp.status_code == 400


class TestProxyIntegration:
    def test_proxy_invalid_url_returns_error(self):
        resp = client.post("/api/proxy-request", json={
            "url": "not-a-valid-url",
            "method": "GET",
        })
        assert resp.status_code in (400, 422, 500)

    def test_proxy_private_ip_blocked(self):
        resp = client.post("/api/proxy-request", json={
            "url": "http://127.0.0.1:8080/",
            "method": "GET",
        })
        assert resp.status_code in (400, 422, 500)


class TestCryptoEndpoints:
    def test_predict_crypto_sync_missing_deps(self):
        resp = client.get("/api/predict-crypto?symbol=BTC-USD")
        assert resp.status_code in (200, 500)

    def test_analyze_crypto_trend_sync_missing_deps(self):
        resp = client.get("/api/analyze-crypto-trend?symbol=BTC-USD")
        assert resp.status_code in (200, 500)


class TestNFTIntegration:
    def test_generate_nft_missing_api_key(self):
        resp = client.post("/api/generate-nft", json={
            "prompt": "test",
            "style": "abstract",
            "provider": "gemini",
        })
        assert resp.status_code in (422, 500)


class TestImageIntegration:
    def test_remove_background_missing_deps(self):
        resp = client.post(
            "/api/remove-background",
            files={"image": ("test.png", b"not-a-real-png", "image/png")},
            data={"bg_color": ""},
        )
        assert resp.status_code in (500,)

    def test_remove_watermark_missing_deps(self):
        resp = client.post(
            "/api/remove-watermark",
            files={
                "image": ("test.png", b"not-a-real-png", "image/png"),
                "mask": ("mask.png", b"not-a-real-png", "image/png"),
            },
            data={"algorithm": "telea"},
        )
        assert resp.status_code in (500,)