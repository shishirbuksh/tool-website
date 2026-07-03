"""Sitemap XML, robots.txt, and llms.txt builder with file-mtime-based lastmod and TTL caching."""

import os
import time
from datetime import UTC, datetime
from html import escape

from app.core.config import Settings
from app.core.tool_data import ToolDataLoader


class SitemapService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._sitemap_cache: tuple[float, str] | None = None
        self._robots_cache: tuple[float, str] | None = None
        self._llms_cache: tuple[float, str] | None = None
        self._dir_cache: dict[str, tuple[float, list[str]]] = {}
        self._cache_ttl = 3600
        self._dir_cache_ttl = 300

    def _from_cache(self, cache) -> str | None:
        if cache and (time.time() - cache[0]) < self._cache_ttl:
            return cache[1]
        return None

    def _get_cached_dir_listing(self, directory: str) -> list[str]:
        now = time.time()
        cached = self._dir_cache.get(directory)
        if cached and now - cached[0] < self._dir_cache_ttl:
            return cached[1]
        if os.path.exists(directory):
            files = sorted(os.listdir(directory))
            self._dir_cache[directory] = (now, files)
            return files
        return []

    def _get_lastmod(self, filepath: str) -> str | None:
        try:
            return datetime.fromtimestamp(os.path.getmtime(filepath), tz=UTC).strftime("%Y-%m-%d")
        except OSError:
            return None

    def _get_changefreq(self, slug: str) -> str:
        return "weekly"

    def build_sitemap_xml(self) -> str:
        cached = self._from_cache(self._sitemap_cache)
        if cached:
            return cached

        pages = []
        pages.append({"loc": "/", "priority": "1.0", "changefreq": "weekly", "filepath": os.path.join(self.settings.templates_dir, "index.html")})
        pages.append({"loc": "/tools", "priority": "0.9", "changefreq": "weekly", "filepath": os.path.join(self.settings.templates_dir, "tools.html")})

        hub_pages = list(self.settings.HUB_CATEGORIES.keys())
        hub_filepath = os.path.join(self.settings.templates_dir, "hub.html")
        for hub in hub_pages:
            pages.append({"loc": f"/{hub}", "priority": "0.6", "changefreq": "weekly", "filepath": hub_filepath})

        tools_dir = os.path.join(self.settings.templates_dir, "tools")
        if os.path.exists(tools_dir):
            for f in self._get_cached_dir_listing(tools_dir):
                if f.endswith(".html"):
                    slug = f[:-5].replace("_", "-")
                    priority = ToolDataLoader.get_priority(slug)
                    info = ToolDataLoader.get(slug)
                    yaml_date = info.get("date_modified") if info else None
                    pages.append({
                        "loc": f"/tool/{slug}",
                        "priority": str(priority),
                        "changefreq": self._get_changefreq(slug),
                        "filepath": os.path.join(tools_dir, f),
                        "yaml_date": yaml_date,
                    })

        pages_dir = os.path.join(self.settings.templates_dir, "pages")
        skip_pages = {"sitemap", "404", "offline", "privacy", "terms", "disclaimer"}
        if os.path.exists(pages_dir):
            for f in self._get_cached_dir_listing(pages_dir):
                if f.endswith(".html"):
                    slug = f[:-5]
                    if slug not in skip_pages:
                        pages.append({
                            "loc": f"/{slug}",
                            "priority": "0.4",
                            "changefreq": "monthly",
                            "filepath": os.path.join(pages_dir, f),
                        })

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?xml-stylesheet type="text/xsl" href="/static/sitemap.xsl"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for page in pages:
            lines.append("  <url>")
            loc_url = escape(f"{self.settings.SITE_URL.rstrip('/')}{page['loc']}")
            lines.append(f"    <loc>{loc_url}</loc>")

            yaml_date = page.get("yaml_date")
            filepath = page.get("filepath")
            if yaml_date:
                lines.append(f"    <lastmod>{yaml_date}</lastmod>")
            elif filepath:
                lastmod = self._get_lastmod(filepath)
                if lastmod:
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
            f"Disallow: /api/\n"
            f"\n"
            f"Sitemap: {self.settings.SITE_URL.rstrip('/')}/sitemap.xml\n"
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
                        lines.append(f"- [{info['name']}]({self.settings.SITE_URL.rstrip('/')}/tool/{slug}): {desc}")
                    else:
                        name = slug.replace("-", " ").title()
                        lines.append(f"- [{name}]({self.settings.SITE_URL.rstrip('/')}/tool/{slug})")

        content = "\n".join(lines)
        self._llms_cache = (time.time(), content)
        return content
