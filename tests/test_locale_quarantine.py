"""End-to-end quarantine contract for localized pages."""

from __future__ import annotations

import re

import pytest


def _h1_text(html: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
    assert match, "missing H1"
    return re.sub(r"<[^>]+>", " ", match.group(1)).strip()


class TestQuarantineContract:
    def test_localized_pages_are_noindex_follow(self, client):
        paths = [
            "/de/",
            "/de/tools",
            "/de/blog",
            "/de/blog/calculators/emi-calculator-guide",
            "/de/calculators",
            "/de/tool/emi-calculator",
        ]
        for path in paths:
            r = client.get(path)
            assert r.status_code == 200, path
            assert r.headers.get("X-Robots-Tag") == "noindex, follow", path
            assert 'content="noindex, follow"' in r.text, path
            assert 'hreflang="de"' not in r.text, path

    def test_localized_sitemaps_are_not_published(self, client):
        for loc in ("hi", "es", "fr", "de"):
            assert client.get(f"/sitemap-{loc}.xml").status_code == 404, loc
        index = client.get("/sitemap-index.xml").text
        for loc in ("hi", "es", "fr", "de"):
            assert f"sitemap-{loc}.xml" not in index, loc
        robots = client.get("/robots.txt").text
        for loc in ("hi", "es", "fr", "de"):
            assert f"sitemap-{loc}.xml" not in robots, loc

    def test_english_page_does_not_advertise_quarantined_alternates(self, client):
        r = client.get("/tool/emi-calculator")
        assert r.status_code == 200
        assert "X-Robots-Tag" not in r.headers
        assert 'hreflang="en"' in r.text
        assert 'hreflang="x-default"' in r.text
        for loc in ("hi", "es", "fr", "de"):
            assert f'hreflang="{loc}"' not in r.text, loc

    def test_localized_h1_uses_localized_seo_name(self, client):
        r = client.get("/de/tool/emi-calculator")
        assert _h1_text(r.text) == "Kreditrechner"
        assert "LSI:" not in r.text

    def test_released_locale_renders_indexable(self, client, monkeypatch):
        from app.api.routes import pages as pages_route

        monkeypatch.setattr(pages_route, "is_path_indexable", lambda loc, path: True)
        monkeypatch.setattr(pages_route, "indexable_locales_for_path", lambda path: ["en", "de"])

        r = client.get("/de/tool/emi-calculator")
        assert r.status_code == 200
        assert "X-Robots-Tag" not in r.headers
        assert 'hreflang="de"' in r.text
        assert 'hreflang="x-default"' in r.text
        assert 'content="index, follow"' in r.text


class TestReleasePath:
    @pytest.fixture(autouse=True)
    def _clear_policy_cache(self):
        from app.core import locale_policy

        locale_policy.clear_cache()
        yield
        locale_policy.clear_cache()

    def test_released_surfaces_index_but_unpublished_items_stay_quarantined(
        self, client, tmp_path, monkeypatch
    ):
        from app.api.routes import seo as seo_routes
        from app.core import locale_policy
        from app.core.config import settings
        from app.services.sitemap_service import SitemapService

        config = tmp_path / "locale_publication.yaml"
        config.write_text(
            "version: 1\n"
            "locales:\n"
            "  en: {status: published}\n"
            "  de:\n"
            "    status: published\n"
            "    surfaces: [home, tools, blog, blog_pillars, hubs, static]\n"
            "    static_pages: [/privacy]\n"
            "  hi: {status: quarantined}\n"
            "  es: {status: quarantined}\n"
            "  fr: {status: quarantined}\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(locale_policy, "_config_path", lambda: str(config))
        monkeypatch.setattr(seo_routes, "sitemap_service", SitemapService(settings))

        # Released surface: indexable, DE alternate present, no quarantine header.
        home = client.get("/de/")
        assert home.status_code == 200
        assert "X-Robots-Tag" not in home.headers
        assert 'hreflang="de"' in home.text
        assert 'content="index, follow"' in home.text

        # Locale is released, but the tool pack has no published translation_status.
        tool = client.get("/de/tool/emi-calculator")
        assert tool.status_code == 200
        assert tool.headers.get("X-Robots-Tag") == "noindex, follow"
        assert 'hreflang="de"' not in tool.text

        # Locale sitemap lists released surfaces only.
        sitemap = client.get("/sitemap-de.xml")
        assert sitemap.status_code == 200
        assert "/de/tools" in sitemap.text
        assert "/de/blog" in sitemap.text
        assert "/de/tool/emi-calculator" not in sitemap.text
        assert "sitemap-de.xml" in client.get("/sitemap-index.xml").text
        assert "sitemap-de.xml" in client.get("/robots.txt").text

        # Per-page allowlist cannot override the English-fallback safety net:
        # /privacy is explicitly allowlisted but still serves English copy.
        privacy = client.get("/de/privacy")
        assert privacy.status_code == 200
        assert privacy.headers.get("X-Robots-Tag") == "noindex, follow"
        assert 'hreflang="de"' not in privacy.text
        assert "/de/privacy" not in sitemap.text

        # EN advertises the released surface cluster, not the unpublished tool.
        en_home = client.get("/")
        assert 'hreflang="de"' in en_home.text
        en_tool = client.get("/tool/emi-calculator")
        assert 'hreflang="de"' not in en_tool.text

    def test_published_item_indexes_when_surfaces_are_empty(self, client, tmp_path, monkeypatch):
        """The 8-tool release: locale published, surfaces [], item published.

        Only the reviewed tool may become indexable. Hubs, home, blog and every
        other review-status item must stay quarantined and absent from the
        locale sitemap, sitemap index, robots.txt and hreflang clusters.
        """
        import copy

        from app.api.routes import seo as seo_routes
        from app.core import locale_policy
        from app.core.config import settings
        from app.services.sitemap_service import SitemapService

        config = tmp_path / "locale_publication.yaml"
        config.write_text(
            "version: 1\n"
            "locales:\n"
            "  en: {status: published}\n"
            "  de:\n"
            "    status: published\n"
            "    surfaces: []\n"
            "  hi: {status: quarantined}\n"
            "  es: {status: quarantined}\n"
            "  fr: {status: quarantined}\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(locale_policy, "_config_path", lambda: str(config))
        monkeypatch.setattr(seo_routes, "sitemap_service", SitemapService(settings))

        # Simulate native sign-off for exactly one tool without mutating the
        # shared YAML cache used by other tests.
        original_tool_raw = locale_policy._tool_raw

        def published_emi(slug: str):
            raw = original_tool_raw(slug)
            if slug != "emi-calculator":
                return raw
            raw = copy.deepcopy(raw)
            raw.setdefault("i18n", {}).setdefault("de", {})["translation_status"] = "published"
            return raw

        monkeypatch.setattr(locale_policy, "_tool_raw", published_emi)

        base = settings.SITE_URL.rstrip("/")
        tool = client.get("/de/tool/emi-calculator")
        assert tool.status_code == 200
        assert "X-Robots-Tag" not in tool.headers
        assert 'content="index, follow"' in tool.text
        assert f'<link rel="canonical" href="{base}/de/tool/emi-calculator">' in tool.text
        assert 'hreflang="de"' in tool.text
        assert 'hreflang="x-default"' in tool.text

        # Empty surfaces: locale-wide chrome remains noindex even though the
        # locale itself is published.
        for path in ("/de/", "/de/tools", "/de/blog", "/de/calculators"):
            page = client.get(path)
            assert page.status_code == 200, path
            assert page.headers.get("X-Robots-Tag") == "noindex, follow", path
            assert 'hreflang="de"' not in page.text, path

        # Review-status tools stay quarantined too.
        other = client.get("/de/tool/debt-calculator")
        assert other.status_code == 200
        assert other.headers.get("X-Robots-Tag") == "noindex, follow"
        assert 'hreflang="de"' not in other.text

        # Locale sitemap contains only the published tool URL.
        sitemap = client.get("/sitemap-de.xml")
        assert sitemap.status_code == 200
        assert f"{base}/de/tool/emi-calculator</loc>" in sitemap.text
        assert "/de/tool/debt-calculator" not in sitemap.text
        assert "/de/tools" not in sitemap.text
        assert "/de/blog" not in sitemap.text
        assert "/de/calculators" not in sitemap.text
        assert f"{base}/de/</loc>" not in sitemap.text
        assert 'hreflang="de"' in sitemap.text
        assert 'hreflang="en"' in sitemap.text
        assert 'hreflang="x-default"' in sitemap.text

        # The locale sitemap is advertised, but no unreleased surface leaks in.
        assert "sitemap-de.xml" in client.get("/sitemap-index.xml").text
        robots = client.get("/robots.txt").text
        assert "sitemap-de.xml" in robots
        assert "Allow: /de/tools" not in robots
        assert "Allow: /de/blog" not in robots

        # EN may advertise the published DE item, never the unreleased surface.
        en_tool = client.get("/tool/emi-calculator")
        assert 'hreflang="de"' in en_tool.text
        en_home = client.get("/")
        assert 'hreflang="de"' not in en_home.text

