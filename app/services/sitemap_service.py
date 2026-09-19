"""Sitemap XML, robots.txt, and llms.txt builder with file-mtime-based lastmod and TTL caching."""

import os
import re
import threading
import time
from datetime import UTC, datetime
from html import escape

from app.core.config import Settings
from app.core.tool_data import ToolDataLoader

_YAML_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SitemapService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._sitemap_cache: tuple[float, str] | None = None
        self._robots_cache: tuple[float, str] | None = None
        self._llms_cache: tuple[float, str] | None = None
        self._dir_cache: dict[str, tuple[float, list[str]]] = {}
        self._cache_ttl = 3600
        self._dir_cache_ttl = 300
        self._lock = threading.Lock()

    def _is_valid_yaml_date(self, value: str | None) -> bool:
        if not value or not _YAML_DATE_RE.match(value):
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _from_cache(self, cache: tuple[float, str] | None) -> str | None:
        # Caller should hold _lock for full check-and-set, but allow lock-free read here
        # since assignment of tuple is atomic under GIL; keep simple thread-safe read.
        with self._lock:
            if cache and (time.time() - cache[0]) < self._cache_ttl:
                return cache[1]
        return None

    def _get_cached_dir_listing(self, directory: str) -> list[str]:
        now = time.time()
        with self._lock:
            cached = self._dir_cache.get(directory)
            if cached and now - cached[0] < self._dir_cache_ttl:
                return cached[1]
        if os.path.exists(directory):
            try:
                files = sorted(os.listdir(directory))
            except OSError:
                return []
            with self._lock:
                self._dir_cache[directory] = (now, files)
            return files
        return []


    def _get_lastmod(self, filepath: str) -> str | None:
        try:
            return datetime.fromtimestamp(os.path.getmtime(filepath), tz=UTC).strftime("%Y-%m-%d")
        except OSError:
            return None

    def _get_changefreq(self, slug: str) -> str:
        # Tools update frequently; standalone pages rarely.
        if slug.startswith("/") and not slug.startswith("/tool/"):
            return "monthly"
        return "weekly"

    def build_sitemap_xml(self) -> str:
        cached = self._from_cache(self._sitemap_cache)
        if cached:
            return cached

        pages = []
        index_path = os.path.join(self.settings.templates_dir, "index.html")
        pages.append({"loc": "/", "priority": "1.0", "changefreq": "weekly", "filepath": index_path})
        sitemap_path = os.path.join(self.settings.templates_dir, "pages", "sitemap.html")
        pages.append({"loc": "/sitemap", "priority": "0.5", "changefreq": "monthly", "filepath": sitemap_path})

        hub_pages = list(self.settings.HUB_CATEGORIES.keys())
        hub_filepath = os.path.join(self.settings.templates_dir, "hub.html")
        for hub in hub_pages:
            if hub == "pdf-tools":
                continue  # legacy alias 301s to /productivity-tools — don't index
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
        skip_pages = {"sitemap", "404", "offline"}
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

        try:
            from app.services.blog_service import BlogService  # noqa: PLC0415

            blog_svc = BlogService(self.settings)
            blog_tpl_dir = os.path.join(self.settings.templates_dir, "blog")
            pages.append({
                "loc": "/blog",
                "priority": "0.8",
                "changefreq": "weekly",
                "filepath": os.path.join(blog_tpl_dir, "index.html"),
            })
            for pillar in blog_svc.get_pillars():
                pages.append({
                    "loc": f"/blog/{pillar}",
                    "priority": "0.6",
                    "changefreq": "weekly",
                    "filepath": os.path.join(blog_tpl_dir, "pillar.html"),
                })
            for post in blog_svc.get_all():
                pages.append({
                    "loc": f"/blog/{post.pillar}/{post.slug}",
                    "priority": "0.5",
                    "changefreq": self._get_changefreq(post.slug),
                    "filepath": os.path.join(blog_tpl_dir, "post.html"),
                    "yaml_date": post.date_modified or None,
                })
        except Exception:
            from app.core.log import get_logger
            logger = get_logger(__name__)
            logger.exception("Failed to build sitemap blog entries")

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
            lastmod = None
            if yaml_date and self._is_valid_yaml_date(str(yaml_date)):
                lastmod = str(yaml_date)
            elif filepath:
                lastmod = self._get_lastmod(filepath)
            if lastmod:
                lines.append(f"    <lastmod>{escape(lastmod)}</lastmod>")

            lines.append(f"    <changefreq>{page['changefreq']}</changefreq>")
            lines.append(f"    <priority>{page['priority']}</priority>")
            lines.append("  </url>")
        lines.append("</urlset>")

        xml_content = "\n".join(lines)
        with self._lock:
            self._sitemap_cache = (time.time(), xml_content)
        return xml_content

    def build_robots_txt(self) -> str:
        cached = self._from_cache(self._robots_cache)
        if cached:
            return cached

        site_url = self.settings.SITE_URL.rstrip('/')
        content = (
            f"User-agent: *\n"
            f"Disallow: /api/\n"
            f"Disallow: /offline\n"
            f"Disallow: /*?*\n"
            f"Disallow: /pdf-tools\n"
            f"\n"
            f"Sitemap: {site_url}/sitemap.xml\n"
        )
        with self._lock:
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
            "> Discover 100+ free AI-powered tools, calculators, and business utilities.",
            "",
            "## Tools",
        ]
        if os.path.exists(tools_dir):
            for f in self._get_cached_dir_listing(tools_dir):
                if f.endswith(".html"):
                    slug = f[:-5].replace("_", "-")
                    info = ToolDataLoader.get(slug)
                    name = info.get("name") if isinstance(info, dict) else None
                    if not name:
                        name = slug.replace("-", " ").title()
                    desc = info.get("description", "") if isinstance(info, dict) else ""
                    link = f"{self.settings.SITE_URL.rstrip('/')}/tool/{slug}"
                    if desc:
                        lines.append(f"- [{name}]({link}): {desc}")
                    else:
                        lines.append(f"- [{name}]({link})")


        content = "\n".join(lines)
        with self._lock:
            self._llms_cache = (time.time(), content)
        return content
