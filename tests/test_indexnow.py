"""Tests for the IndexNow key file endpoint (Bing/Yandex ownership verification)."""

from app.api.routes import seo as seo_routes

TEST_KEY = "0123456789abcdef0123456789abcdef"


class TestIndexNowKeyFile:
    def test_key_file_404_when_unconfigured(self, client, monkeypatch):
        monkeypatch.setattr(seo_routes.settings, "INDEXNOW_KEY", "")
        resp = client.get(f"/{TEST_KEY}.txt")
        assert resp.status_code == 404

    def test_key_file_serves_configured_key(self, client, monkeypatch):
        monkeypatch.setattr(seo_routes.settings, "INDEXNOW_KEY", TEST_KEY)
        resp = client.get(f"/{TEST_KEY}.txt")
        assert resp.status_code == 200
        assert resp.text == TEST_KEY
        assert resp.headers["content-type"].startswith("text/plain")

    def test_key_file_rejects_wrong_key(self, client, monkeypatch):
        monkeypatch.setattr(seo_routes.settings, "INDEXNOW_KEY", TEST_KEY)
        resp = client.get("/ffffffffffffffffffffffffffffffff.txt")
        assert resp.status_code == 404

    def test_key_file_rejects_non_hex(self, client, monkeypatch):
        monkeypatch.setattr(seo_routes.settings, "INDEXNOW_KEY", TEST_KEY)
        resp = client.get("/not-a-real-key!!.txt")
        assert resp.status_code == 404

    def test_robots_txt_still_served(self, client, monkeypatch):
        # Route precedence: /robots.txt must hit the static handler, not /{key}.txt.
        monkeypatch.setattr(seo_routes.settings, "INDEXNOW_KEY", TEST_KEY)
        resp = client.get("/robots.txt")
        assert resp.status_code == 200
        assert "User-agent" in resp.text
