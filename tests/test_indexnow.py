"""Tests for the IndexNow key file endpoint and English-only submission script."""

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
        monkeypatch.setattr(seo_routes.settings, "INDEXNOW_KEY", TEST_KEY)
        resp = client.get("/robots.txt")
        assert resp.status_code == 200
        assert "User-agent" in resp.text


class TestIndexNowEnglishOnly:
    def test_sitemap_urls_for_returns_en_only(self):
        from scripts import submit_indexnow

        assert submit_indexnow.sitemap_urls_for("www.storybrainai.com", include_all=True) == [
            "https://www.storybrainai.com/sitemap.xml"
        ]
        assert submit_indexnow.sitemap_urls_for("www.storybrainai.com", include_all=False) == []

    def test_skips_legacy_locale_redirect_urls(self, monkeypatch):
        from scripts import submit_indexnow

        posted: list[list[str]] = []

        def fake_post(*, key, host, key_location, urls, timeout, dry_run):
            posted.append(urls)
            return 200

        monkeypatch.setattr(submit_indexnow, "post_chunk", fake_post)
        en_url = "https://www.storybrainai.com/tool/emi-calculator"
        de_url = "https://www.storybrainai.com/de/tool/emi-calculator"
        hi_url = "https://www.storybrainai.com/hi/tool/emi-calculator"
        rc = submit_indexnow.main(["--key", TEST_KEY, "--url", de_url, "--url", en_url, "--url", hi_url, "--dry-run"])
        assert rc == 0
        assert posted == [[en_url]]
