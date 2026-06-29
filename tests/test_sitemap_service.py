"""Tests for SitemapService: XML structure, robots.txt, llms.txt generation, and content validation."""

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
