"""Tests for SitemapService: XML structure, robots.txt, llms.txt generation, and content validation."""

import re

from app.services.sitemap_service import SitemapService


class TestSitemapService:
    def test_build_sitemap_xml_returns_string(self, settings):
        svc = SitemapService(settings)
        result = svc.build_sitemap_xml()
        assert isinstance(result, str)
        assert result.startswith("<?xml")
        assert "urlset" in result

    def test_sitemap_xml_contains_base_url(self, settings):
        svc = SitemapService(settings)
        result = svc.build_sitemap_xml()
        assert "storybrainai.com" in result

    def test_sitemap_xml_contains_homepage(self, settings):
        svc = SitemapService(settings)
        result = svc.build_sitemap_xml()
        assert "/tool/" in result

    def test_sitemap_xml_well_formed(self, settings):
        svc = SitemapService(settings)
        result = svc.build_sitemap_xml()
        assert result.count("<url>") == result.count("</url>")
        assert result.count("<urlset") > 0
        assert result.count("</urlset>") > 0

    def test_build_robots_txt_returns_string(self, settings):
        svc = SitemapService(settings)
        result = svc.build_robots_txt()
        assert isinstance(result, str)
        assert "Sitemap" in result
        assert "User-agent" in result

    def test_robots_txt_contains_base_url(self, settings):
        svc = SitemapService(settings)
        result = svc.build_robots_txt()
        assert "storybrainai.com" in result

    def test_robots_txt_disallows_api(self, settings):
        svc = SitemapService(settings)
        result = svc.build_robots_txt()
        assert "Disallow: /api/" in result

    def test_build_llms_txt_returns_string(self, settings):
        svc = SitemapService(settings)
        result = svc.build_llms_txt()
        assert isinstance(result, str)
        assert "StoryBrain" in result

    def test_llms_txt_contains_tools(self, settings):
        svc = SitemapService(settings)
        result = svc.build_llms_txt()
        assert "/tool/" in result

    def test_tools_priority_08_weekly(self, settings):
        svc = SitemapService(settings)
        result = svc.build_sitemap_xml()
        m = re.search(r"<loc>(https://[^<]*/tools)</loc>\s*<lastmod>[^<]*</lastmod>\s*<changefreq>([^<]*)</changefreq>\s*<priority>([^<]*)</priority>", result)
        assert m, "/tools entry missing"
        assert m.group(2) == "weekly", m.group(2)
        assert m.group(3) == "0.8", m.group(3)

    def test_blog_posts_changefreq_monthly(self, settings):
        svc = SitemapService(settings)
        result = svc.build_sitemap_xml()
        freqs = re.findall(r"<loc>(https://[^<]*/blog/[^/<]*\/[^<]*)</loc>\s*<lastmod>[^<]*</lastmod>\s*<changefreq>([^<]*)</changefreq>", result)
        assert freqs, "no blog post entries"
        bad = [loc for loc, freq in freqs if freq != "monthly"]
        assert not bad, f"non-monthly blog entries: {bad[:5]}"

    def test_llms_has_guides_and_categories(self, settings):
        svc = SitemapService(settings)
        result = svc.build_llms_txt()
        assert "## Guides" in result
        assert "## Categories" in result
        assert "/blog/calculators/emi-calculator-guide" in result
        assert "/calculators" in result
