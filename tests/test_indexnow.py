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


class TestIndexNowLocalePolicy:
    def test_released_helper_filters_english(self, monkeypatch):
        import app.core.locale_policy as policy
        from scripts import submit_indexnow

        monkeypatch.setattr(policy, "published_locales", lambda: ["en", "de", "es"])
        assert submit_indexnow.released_i18n_locales() == ["de", "es"]

    def test_released_helper_fails_closed(self, monkeypatch):
        import app.core.locale_policy as policy
        from scripts import submit_indexnow

        def boom():
            raise RuntimeError("bad config")

        monkeypatch.setattr(policy, "published_locales", boom)
        assert submit_indexnow.released_i18n_locales() == []

    def test_all_locales_only_submits_released_sitemaps(self, monkeypatch):
        from scripts import submit_indexnow

        fetched: list[str] = []

        def fake_fetch(url, _timeout, _depth=0):
            fetched.append(url)
            return ["https://www.storybrainai.com/tool/emi-calculator"]

        monkeypatch.setattr(submit_indexnow, "released_i18n_locales", lambda: ["de"])
        monkeypatch.setattr(submit_indexnow, "fetch_sitemap_locs", fake_fetch)
        rc = submit_indexnow.main(["--key", TEST_KEY, "--all-locales", "--dry-run", "--timeout", "1"])
        assert rc == 0
        assert fetched == ["https://www.storybrainai.com/sitemap-de.xml"]

    def test_explicit_quarantined_locale_is_skipped(self, monkeypatch):
        from scripts import submit_indexnow

        fetched: list[str] = []
        monkeypatch.setattr(submit_indexnow, "released_i18n_locales", lambda: [])
        monkeypatch.setattr(submit_indexnow, "fetch_sitemap_locs", lambda *args, **kwargs: fetched.append(args[0]) or [])
        rc = submit_indexnow.main(
            [
                "--key",
                TEST_KEY,
                "--locale",
                "hi",
                "--url",
                "https://www.storybrainai.com/tool/emi-calculator",
                "--dry-run",
                "--timeout",
                "1",
            ]
        )
        assert rc == 0
        assert fetched == []

    def test_explicit_urls_under_quarantined_locale_are_skipped(self, monkeypatch):
        from scripts import submit_indexnow

        posted: list[list[str]] = []
        en_url = "https://www.storybrainai.com/tool/emi-calculator"
        de_url = "https://www.storybrainai.com/de/tool/emi-calculator"
        hi_url = "https://www.storybrainai.com/hi/tool/emi-calculator"
        monkeypatch.setattr(submit_indexnow, "released_i18n_locales", lambda: ["de"])
        monkeypatch.setattr(submit_indexnow, "post_chunk", lambda **kwargs: posted.append(kwargs["urls"]) or 200)
        rc = submit_indexnow.main(
            ["--key", TEST_KEY, "--url", en_url, "--url", de_url, "--url", hi_url, "--dry-run", "--timeout", "1"]
        )
        assert rc == 0
        assert posted == [[en_url, de_url]]
