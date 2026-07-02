"""Sitemap XML, robots.txt, and llms.txt builder with file-mtime-based lastmod and TTL caching."""

import os
import time
from datetime import UTC, datetime

from app.core.config import Settings
from app.core.tool_data import ToolDataLoader


class SitemapService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._sitemap_cache: tuple[float, str] | None = None
        self._robots_cache: tuple[float, str] | None = None
        self._llms_cache: tuple[float, str] | None = None
        self._dir_cache: tuple[float, list[str]] | None = None
        self._cache_ttl = 3600
        self._dir_cache_ttl = 300

    def _from_cache(self, cache) -> str | None:
        if cache and (time.time() - cache[0]) < self._cache_ttl:
            return cache[1]
        return None

    def _get_cached_dir_listing(self, directory: str) -> list[str]:
        now = time.time()
        if self._dir_cache and now - self._dir_cache[0] < self._dir_cache_ttl:
            return self._dir_cache[1]
        if os.path.exists(directory):
            files = sorted(os.listdir(directory))
            self._dir_cache = (now, files)
            return files
        return []

    def _get_lastmod(self, filepath: str) -> str:
        try:
            return datetime.fromtimestamp(os.path.getmtime(filepath), tz=UTC).strftime("%Y-%m-%d")
        except OSError:
            return datetime.now(UTC).strftime("%Y-%m-%d")

    def _get_changefreq(self, slug: str) -> str:
        return "weekly"

    def build_sitemap_xml(self) -> str:
        cached = self._from_cache(self._sitemap_cache)
        if cached:
            return cached

        pages = []
        pages.append({"loc": "/", "priority": "1.0", "changefreq": "weekly"})

        hub_pages = list(self.settings.HUB_CATEGORIES.keys())
        for hub in hub_pages:
            pages.append({"loc": f"/{hub}", "priority": "0.6", "changefreq": "weekly"})

        tools_dir = os.path.join(self.settings.templates_dir, "tools")
        if os.path.exists(tools_dir):
            for f in self._get_cached_dir_listing(tools_dir):
                if f.endswith(".html"):
                    slug = f[:-5].replace("_", "-")
                    priority = ToolDataLoader.get_priority(slug)
                    pages.append({
                        "loc": f"/tool/{slug}",
                        "priority": str(priority),
                        "changefreq": self._get_changefreq(slug),
                        "filepath": os.path.join(tools_dir, f),
                    })

        pages_dir = os.path.join(self.settings.templates_dir, "pages")
        legal_pages = {"privacy", "terms", "disclaimer"}
        skip_pages = {"sitemap", "404", "offline"}
        if os.path.exists(pages_dir):
            for f in self._get_cached_dir_listing(pages_dir):
                if f.endswith(".html"):
                    slug = f[:-5]
                    if slug not in skip_pages:
                        pages.append({
                            "loc": f"/{slug}",
                            "priority": "0.5" if slug in legal_pages else "0.4",
                            "changefreq": "yearly" if slug in legal_pages else "monthly",
                            "filepath": os.path.join(pages_dir, f),
                        })

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?xml-stylesheet type="text/xsl" href="/static/sitemap.xsl"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for page in pages:
            filepath = page.get("filepath")
            if filepath:
                lastmod = self._get_lastmod(filepath) or datetime.now(UTC).strftime("%Y-%m-%d")
            else:
                lastmod = datetime.now(UTC).strftime("%Y-%m-%d")
            lines.append("  <url>")
            lines.append(f"    <loc>{self.settings.SITE_URL}{page['loc']}</loc>")
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
            lines.append(f"    <changefreq>{page['changefreq']}</changefreq>")
            lines.append(f"    <priority>{page['priority']}</priority>")
            lines.append("  </url>")
        lines.append("</urlset>")

        xml_content = "\n".join(lines)
        self._sitemap_cache = (time.time(), xml_content)
        return xml_content

    def build_robots_txt(self) -> str:
        cached = self._from_cache(self._robots_cache)
        if cached:
            return cached

        content = (
            f"User-agent: *\n"
            f"Allow: /\n"
            f"Disallow: /api/\n"
            f"Crawl-Delay: 10\n"
            f"\n"
            f"Sitemap: {self.settings.SITE_URL}/sitemap.xml\n"
        )
        self._robots_cache = (time.time(), content)
        return content

    def build_llms_txt(self) -> str:
        cached = self._from_cache(self._llms_cache)
        if cached:
            return cached

        tools_dir = os.path.join(self.settings.templates_dir, "tools")
        lines = [
            "# StoryBrain AI — AI Tool Directory",
            "",
            "> Discover 70+ free AI-powered tools, calculators, and business utilities.",
            "",
            "## Tools",
        ]
        if os.path.exists(tools_dir):
            for f in self._get_cached_dir_listing(tools_dir):
                if f.endswith(".html"):
                    slug = f[:-5].replace("_", "-")
                    info = ToolDataLoader.get(slug)
                    if info:
                        desc = info.get("description", "")
                        lines.append(f"- [{info['name']}]({self.settings.SITE_URL}/tool/{slug}): {desc}")
                    else:
                        name = slug.replace("-", " ").title()
                        lines.append(f"- [{name}]({self.settings.SITE_URL}/tool/{slug})")

        content = "\n".join(lines)
        self._llms_cache = (time.time(), content)
        return content
