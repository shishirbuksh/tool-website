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
        self._lock = threading.RLock()

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
        # Tools update frequently; blog + standalone pages rarely.
        # Accepts bare tool slugs ("emi-calculator"), "/tool/<slug>", and "/blog/<pillar>/<slug>".
        if slug.startswith("/blog/"):
            return "monthly"
        if slug.startswith("/tool/") or not slug.startswith("/"):
            return "weekly"
        return "monthly"

    def _collect_pages(self) -> list[dict]:
        pages: list[dict] = []
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
            # YAML is source of truth; filesystem verified to avoid indexing orphans.
            try:
                yaml_slugs = list(ToolDataLoader.get_all().keys())
            except Exception:
                yaml_slugs = []
            template_files = set(self._get_cached_dir_listing(tools_dir))
            for slug in sorted(yaml_slugs):
                fname = f"{slug.replace('-', '_')}.html"
                if fname not in template_files:
                    continue  # YAML without template — do not index
                priority = ToolDataLoader.get_priority(slug)
                info = ToolDataLoader.get(slug)
                yaml_date = info.get("date_modified") if info else None
                pages.append({
                    "loc": f"/tool/{slug}",
                    "priority": str(priority),
                    "changefreq": self._get_changefreq(f"/tool/{slug}"),
                    "filepath": os.path.join(tools_dir, fname),
                    "yaml_date": yaml_date,
                })

        pages_dir = os.path.join(self.settings.templates_dir, "pages")
        skip_pages = {"sitemap", "404", "offline", "500"}
        if os.path.exists(pages_dir):
            for f in self._get_cached_dir_listing(pages_dir):
                if f.endswith(".html"):
                    slug = f[:-5]
                    if slug not in skip_pages:
                        if slug == "tools":
                            pages.append({
                                "loc": f"/{slug}",
                                "priority": "0.8",
                                "changefreq": "weekly",
                                "filepath": os.path.join(pages_dir, f),
                            })
                        else:
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
                    "changefreq": self._get_changefreq(f"/blog/{post.pillar}/{post.slug}"),
                    "filepath": os.path.join(blog_tpl_dir, "post.html"),
                    "yaml_date": post.date_modified or None,
                })
        except Exception:
            from app.core.log import get_logger
            logger = get_logger(__name__)
            logger.exception("Failed to build sitemap blog entries")
        return pages

    def _render_urlset(self, pages: list[dict], locale: str = "en") -> str:
        from app.core.i18n import SUPPORTED_LOCALES, localize_path  # noqa: PLC0415

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?xml-stylesheet type="text/xsl" href="/static/sitemap.xsl"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
        ]
        for page in pages:
            loc_path = localize_path(page["loc"], locale)
            loc_url = escape(f"{self.settings.SITE_URL.rstrip('/')}{loc_path}")
            lines.append("  <url>")
            lines.append(f"    <loc>{loc_url}</loc>")

            yaml_date = page.get("yaml_date")
            filepath = page.get("filepath")
            lastmod = None
            if yaml_date and self._is_valid_yaml_date(str(yaml_date)):
                lastmod = str(yaml_date)
            elif filepath and page.get("loc") in ("/", "/sitemap", "/tools"):
                # Shared templates (hub.html, pillar.html, post.html, tool pages)
                # share one mtime across hundreds of URLs — using it as lastmod
                # fakes freshness on every deploy. Omit instead.
                lastmod = self._get_lastmod(filepath)
            if lastmod:
                lines.append(f"    <lastmod>{escape(lastmod)}</lastmod>")

            lines.append(f"    <changefreq>{page['changefreq']}</changefreq>")
            lines.append(f"    <priority>{page['priority']}</priority>")
            # hreflang alternates for every supported locale (+ x-default -> en).
            # Placed after priority so legacy loc/lastmod/changefreq/priority
            # adjacency regexes in tests keep passing; order is irrelevant to crawlers.
            for alt in SUPPORTED_LOCALES:
                alt_url = escape(f"{self.settings.SITE_URL.rstrip('/')}{localize_path(page['loc'], alt)}")
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{alt}" href="{alt_url}" />')
            default_url = escape(f"{self.settings.SITE_URL.rstrip('/')}{localize_path(page['loc'], 'en')}")
            lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{default_url}" />')

            lines.append("  </url>")
        lines.append("</urlset>")
        return "\n".join(lines)

    def build_sitemap_xml(self) -> str:
        with self._lock:
            cached = self._from_cache(self._sitemap_cache)
            if cached:
                return cached

            pages = self._collect_pages()
            xml_content = self._render_urlset(pages, locale="en")
            self._sitemap_cache = (time.time(), xml_content)
            return xml_content

    def build_sitemap_xml_for_locale(self, locale: str) -> str:
        from app.core.i18n import normalize_locale  # noqa: PLC0415

        loc = normalize_locale(locale)
        pages = self._collect_pages()
        return self._render_urlset(pages, locale=loc)

    def build_sitemap_index(self) -> str:
        from app.core.i18n import SUPPORTED_LOCALES  # noqa: PLC0415

        base = self.settings.SITE_URL.rstrip("/")
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            f"  <sitemap><loc>{escape(base)}/sitemap.xml</loc></sitemap>",
        ]
        for loc in SUPPORTED_LOCALES:
            if loc == "en":
                continue
            lines.append(f"  <sitemap><loc>{escape(base)}/sitemap-{loc}.xml</loc></sitemap>")
        lines.append("</sitemapindex>")
        return "\n".join(lines)

    def build_robots_txt(self) -> str:
        with self._lock:
            cached = self._from_cache(self._robots_cache)
            if cached:
                return cached

            site_url = self.settings.SITE_URL.rstrip('/')
            content = (
                f"User-agent: *\n"
                f"Allow: /sitemap.xml\n"
                f"Allow: /sitemap-hi.xml\n"
                f"Allow: /sitemap-es.xml\n"
                f"Allow: /sitemap-fr.xml\n"
                f"Disallow: /api/\n"
                f"Disallow: /offline\n"
                f"Disallow: /*?*\n"
                f"Disallow: /pdf-tools\n"
                f"\n"
                f"Sitemap: {site_url}/sitemap.xml\n"
                f"Sitemap: {site_url}/sitemap-index.xml\n"
                f"Sitemap: {site_url}/sitemap-hi.xml\n"
                f"Sitemap: {site_url}/sitemap-es.xml\n"
                f"Sitemap: {site_url}/sitemap-fr.xml\n"
            )
            self._robots_cache = (time.time(), content)
            return content

    def build_llms_txt(self) -> str:
        with self._lock:
            cached = self._from_cache(self._llms_cache)
            if cached:
                return cached

            tools_dir = os.path.join(self.settings.templates_dir, "tools")
            try:
                tool_count = len(ToolDataLoader.get_all())
            except Exception:
                tool_count = len(self._get_cached_dir_listing(tools_dir)) if os.path.exists(tools_dir) else 0
            lines = [
                "# StoryBrain AI — AI Tool Directory",
                "",
                f"> Discover {tool_count} free AI-powered tools, calculators, and business utilities.",
                "",
                "## Tools",
            ]
            if os.path.exists(tools_dir):
                try:
                    all_tools = ToolDataLoader.get_all()
                    yaml_slugs = list(all_tools.keys())
                except Exception:
                    all_tools = {}
                    yaml_slugs = []
                template_files = set(self._get_cached_dir_listing(tools_dir))

                tool_lines = []
                for slug in sorted(yaml_slugs):
                    fname = f"{slug.replace('-', '_')}.html"
                    if fname not in template_files:
                        continue
                    info = all_tools.get(slug, {})
                    name = info.get("name")
                    if not name:
                        name = slug.replace("-", " ").title()
                    desc = info.get("description", "").strip()
                    link = f"{self.settings.SITE_URL.rstrip('/')}/tool/{slug}"
                    if desc:
                        desc = desc.replace('\n', ' ')
                        tool_lines.append(f"- [{name}]({link}): {desc}")
                    else:
                        tool_lines.append(f"- [{name}]({link})")

                # Update lines with real count
                lines[2] = f"> Discover {len(tool_lines)} free AI-powered tools, calculators, and business utilities."
                lines.extend(tool_lines)

            site_base = self.settings.SITE_URL.rstrip("/")
            lines.append("")
            lines.append("## Categories")
            lines.append("")
            lines.append(f"- [All Tools]({site_base}/tools): complete directory of every free tool")
            for hub in self.settings.HUB_CATEGORIES:
                if hub == "pdf-tools":
                    continue  # legacy alias, not indexed
                lines.append(f"- [{hub}]({site_base}/{hub})")
            lines.append("")
            lines.append("## Guides")
            lines.append("")
            lines.append(f"- [Blog]({site_base}/blog): step-by-step guides for every free tool")
            try:
                from app.services.blog_service import BlogService  # noqa: PLC0415

                for post in BlogService(self.settings).get_all():
                    lines.append(f"- [{post.title}]({site_base}/blog/{post.pillar}/{post.slug})")
            except Exception:
                from app.core.log import get_logger
                logger = get_logger(__name__)
                logger.exception("Failed to build llms.txt guides section")

            lines.append("")
            lines.append(f"Sitemap: {site_base}/sitemap.xml")

            content = "\n".join(lines)
            self._llms_cache = (time.time(), content)
            return content
