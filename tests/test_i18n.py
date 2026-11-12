"""Tests for pure-English rendering, canonical headers, sitemaps, and zero i18n leakage."""

import pytest

from app.api.routes.pages import catalog_service
from app.core.tool_data import ToolDataLoader


class TestPureEnglishSEO:
    @pytest.mark.parametrize(
        "path",
        ["/", "/tools", "/student-tools", "/calculators", "/blog", "/tool/emi-calculator", "/tool/qr-generator"],
    )
    def test_no_hreflang_or_accept_language_vary(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 200
        assert '<html lang="en"' in resp.text
        assert "hreflang" not in resp.text
        vary = resp.headers.get("vary", "")
        assert "Accept-Language" not in vary
        assert resp.headers.get("content-language") == "en"

    def test_robots_and_sitemap_english_only(self, client):
        robots = client.get("/robots.txt")
        assert robots.status_code == 200
        assert "Sitemap: https://www.storybrainai.com/sitemap.xml" in robots.text
        assert "sitemap-index.xml" not in robots.text
        assert "Disallow: /*?*" not in robots.text
        assert "Disallow: /pdf-tools" not in robots.text
        assert "Disallow: /*/offline" not in robots.text

        sm = client.get("/sitemap.xml")
        assert sm.status_code == 200
        assert "xhtml:link" not in sm.text
        assert "hreflang" not in sm.text
        assert "/hi/" not in sm.text
        assert "/es/" not in sm.text
        assert "/fr/" not in sm.text
        assert "/de/" not in sm.text

    def test_legacy_sitemap_routes(self, client):
        r_idx = client.get("/sitemap-index.xml", follow_redirects=False)
        assert r_idx.status_code == 301
        assert r_idx.headers["location"].endswith("/sitemap.xml")

        r_en = client.get("/sitemap-en.xml", follow_redirects=False)
        assert r_en.status_code == 301
        assert r_en.headers["location"].endswith("/sitemap.xml")

        for loc in ("hi", "es", "fr", "de"):
            assert client.get(f"/sitemap-{loc}.xml").status_code == 404

    def test_yaml_has_no_i18n_blocks_and_dynamic_tool_count(self, client):
        for slug, raw in ToolDataLoader.get_all().items():
            assert "i18n" not in raw, f"{slug} still contains i18n block"
        categories, _ = catalog_service.get_categorized_tools()
        count = sum(len(tools) for tools in categories.values())
        home = client.get("/")
        assert f"{count} " in home.text or f"{count}+" in home.text

    def test_no_duplicate_breadcrumblist_and_paginated_og_url(self, client):
        for path in ("/tools", "/student-tools", "/blog", "/tool/emi-calculator"):
            resp = client.get(path)
            assert resp.status_code == 200
            assert resp.text.count('"BreadcrumbList"') == 1, f"Duplicate BreadcrumbList on {path}"

        p2 = client.get("/blog?page=2")
        assert p2.status_code == 200
        assert 'rel="canonical" href="https://www.storybrainai.com/blog?page=2"' in p2.text
        assert 'property="og:url" content="https://www.storybrainai.com/blog?page=2"' in p2.text
        assert 'name="twitter:url" content="https://www.storybrainai.com/blog?page=2"' in p2.text
