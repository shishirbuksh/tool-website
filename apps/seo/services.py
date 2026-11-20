"""SEO Services: Dynamic XML Sitemaps, robots.txt, llms.txt, and IndexNow."""

from __future__ import annotations

import os
import re
import threading
import time
from datetime import datetime, UTC
from html import escape
from django.conf import settings
from apps.catalog.services import ToolDataLoader
from apps.blog.services import BlogService

_YAML_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SitemapService:
    def __init__(self, settings=None) -> None:
        self.settings = settings
        self._sitemap_cache: tuple[float, str] | None = None
        self._robots_cache: tuple[float, str] | None = None
        self._llms_cache: tuple[float, str] | None = None
        self._cache_ttl = 3600
        self._lock = threading.RLock()

    def _get_lastmod(self, filepath: str) -> str | None:
        try:
            return datetime.fromtimestamp(os.path.getmtime(filepath), tz=UTC).strftime("%Y-%m-%d")
        except OSError:
            return None

    def _collect_pages(self) -> list[dict]:
        pages: list[dict] = []
        templates_dir = os.path.join(settings.BASE_DIR, "templates")

        index_path = os.path.join(templates_dir, "index.html")
        pages.append({"loc": "/", "priority": "1.0", "changefreq": "weekly", "filepath": index_path})

        sitemap_path = os.path.join(templates_dir, "pages", "sitemap.html")
        pages.append({"loc": "/sitemap", "priority": "0.5", "changefreq": "monthly", "filepath": sitemap_path})

        # Hub pages
        hub_categories = getattr(settings, "HUB_CATEGORIES", {})
        hub_path = os.path.join(templates_dir, "hub.html")
        for hub in hub_categories:
            if hub == "pdf-tools":
                continue
            pages.append({"loc": f"/{hub}", "priority": "0.6", "changefreq": "weekly", "filepath": hub_path})

        # Tool pages
        tools_dir = os.path.join(templates_dir, "tools")
        excluded_tools = {
            "love-calculator",
            "crypto-price-prediction",
            "meme-coin-detector",
            "airdrop-finder",
            "crypto-scam-checker",
            "crypto-red-flag-self-assessment-tool",
        }
        if os.path.exists(tools_dir):
            all_slugs = ToolDataLoader.get_slugs()
            for slug in all_slugs:
                if slug in excluded_tools:
                    continue
                fname = f"{slug.replace('-', '_')}.html"
                fpath = os.path.join(tools_dir, fname)
                if os.path.isfile(fpath):
                    info = ToolDataLoader.get(slug) or {}
                    yaml_date = info.get("date_modified")
                    pages.append({
                        "loc": f"/tool/{slug}",
                        "priority": str(info.get("sitemap_priority", 0.7)),
                        "changefreq": "weekly",
                        "filepath": fpath,
                        "yaml_date": yaml_date,
                    })

        # Pages in templates/pages
        pages_dir = os.path.join(templates_dir, "pages")
        skip_pages = {"sitemap", "404", "offline", "500"}
        if os.path.exists(pages_dir):
            for f in sorted(os.listdir(pages_dir)):
                if f.endswith(".html"):
                    slug = f[:-5]
                    if slug not in skip_pages:
                        priority = "0.8" if slug in ("tools", "student-tools") else "0.4"
                        freq = "weekly" if slug in ("tools", "student-tools") else "monthly"
                        pages.append({
                            "loc": f"/{slug}",
                            "priority": priority,
                            "changefreq": freq,
                            "filepath": os.path.join(pages_dir, f),
                        })
            privacy_path = os.path.join(pages_dir, "privacy.html")
            terms_path = os.path.join(pages_dir, "terms.html")
            if os.path.exists(privacy_path):
                pages.append({"loc": "/privacy-policy", "priority": "0.4", "changefreq": "monthly", "filepath": privacy_path})
            if os.path.exists(terms_path):
                pages.append({"loc": "/terms-of-service", "priority": "0.4", "changefreq": "monthly", "filepath": terms_path})

        # Blog posts
        blog_service = BlogService()
        blog_tpl_dir = os.path.join(templates_dir, "blog")
        pages.append({"loc": "/blog", "priority": "0.8", "changefreq": "weekly", "filepath": os.path.join(blog_tpl_dir, "index.html")})
        for pinfo in blog_service.get_pillars():
            pages.append({"loc": f"/blog/{pinfo}", "priority": "0.6", "changefreq": "weekly", "filepath": os.path.join(blog_tpl_dir, "pillar.html")})

        excluded_blog_posts = {
            "love-calculator-explained-fun",
            "crypto-price-prediction-how-it-works",
            "meme-coin-detector-guide",
            "meme-coin-red-flags-learn-guide",
            "airdrop-finder-guide",
        }
        for post in blog_service.get_all():
            if post.slug in excluded_blog_posts:
                continue
            pages.append({
                "loc": f"/blog/{post.pillar}/{post.slug}",
                "priority": "0.5",
                "changefreq": "monthly",
                "filepath": os.path.join(blog_tpl_dir, "post.html"),
                "yaml_date": post.date_modified or None,
            })

        return pages

    def _render_urlset(self, pages: list[dict]) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?xml-stylesheet type="text/xsl" href="/static/sitemap.xsl"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        base = getattr(settings, "SITE_URL", "https://www.storybrainai.com").rstrip("/")
        for page in pages:
            loc_url = escape(f"{base}{page['loc']}")
            lines.append("  <url>")
            lines.append(f"    <loc>{loc_url}</loc>")

            yaml_date = page.get("yaml_date")
            filepath = page.get("filepath")
            lastmod = None
            if filepath and os.path.isfile(filepath) and not filepath.endswith(("hub.html", "pillar.html", "post.html")):
                lastmod = self._get_lastmod(filepath)
            elif yaml_date and _YAML_DATE_RE.match(str(yaml_date)):
                lastmod = str(yaml_date)
            elif filepath and os.path.isfile(filepath):
                lastmod = self._get_lastmod(filepath)

            if lastmod:
                lines.append(f"    <lastmod>{escape(lastmod)}</lastmod>")

            lines.append(f"    <changefreq>{page['changefreq']}</changefreq>")
            lines.append(f"    <priority>{page['priority']}</priority>")
            lines.append("  </url>")
        lines.append("</urlset>")
        return "\n".join(lines)

    def build_sitemap_xml(self) -> str:
        with self._lock:
            now = time.time()
            if self._sitemap_cache and now - self._sitemap_cache[0] < self._cache_ttl:
                return self._sitemap_cache[1]
            pages = self._collect_pages()
            xml = self._render_urlset(pages)
            self._sitemap_cache = (now, xml)
            return xml

    def build_robots_txt(self) -> str:
        with self._lock:
            now = time.time()
            if self._robots_cache and now - self._robots_cache[0] < 60:
                return self._robots_cache[1]
            site_url = getattr(settings, "SITE_URL", "https://www.storybrainai.com").rstrip("/")
            content = (
                "User-agent: *\n"
                "Allow: /ads.txt\n"
                "Allow: /sitemap.xml\n"
                "Allow: /llms.txt\n"
                "Allow: /static/\n"
                "Allow: /static/*\n"
                "Allow: /*.css*\n"
                "Allow: /*.js*\n"
                "Allow: /*.svg*\n"
                "Allow: /*.png*\n"
                "Allow: /*.webp*\n"
                "Allow: /*.jpg*\n"
                "Allow: /*.ico*\n"
                "Allow: /*.woff2*\n"
                "Allow: /sw.js\n"
                "Disallow: /api/\n"
                "Disallow: /offline\n"
                "Disallow: /healthz\n"
                "Disallow: /readyz\n"
                "Disallow: /versionz\n"
                "Disallow: /metrics\n"
                "\n"
                "User-agent: Googlebot\n"
                "Allow: /\n"
                "Allow: /ads.txt\n"
                "\n"
                "User-agent: Mediapartners-Google\n"
                "Allow: /\n"
                "Allow: /ads.txt\n"
                "\n"
                "User-agent: Google-AdSense\n"
                "Allow: /\n"
                "Allow: /ads.txt\n"
                "\n"
                "User-agent: Google-AdSense-Review\n"
                "Allow: /\n"
                "Allow: /ads.txt\n"
                "\n"
                "User-agent: GPTBot\n"
                "User-agent: ClaudeBot\n"
                "User-agent: PerplexityBot\n"
                "User-agent: Applebot-Extended\n"
                "User-agent: Google-Extended\n"
                "Allow: /\n"
                "Allow: /llms.txt\n"
                "Disallow: /api/\n"
                "Disallow: /offline\n"
                "\n"
                f"Sitemap: {site_url}/sitemap.xml\n"
            )
            self._robots_cache = (now, content)
            return content

    def build_llms_txt(self) -> str:
        with self._lock:
            now = time.time()
            if self._llms_cache and now - self._llms_cache[0] < self._cache_ttl:
                return self._llms_cache[1]
            site_url = getattr(settings, "SITE_URL", "https://www.storybrainai.com").rstrip("/")
            all_tools = ToolDataLoader.get_all()
            lines = [
                f"# {getattr(settings, 'PROJECT_NAME', 'StoryBrain AI')} — AI Tool Directory",
                "",
                f"> Discover {len(all_tools)} free AI-powered tools, calculators, and business utilities.",
                "",
                "## Tools",
            ]
            for slug in sorted(all_tools.keys()):
                info = all_tools.get(slug, {})
                name = info.get("name") or slug.replace("-", " ").title()
                desc = (info.get("description") or "").strip().replace("\n", " ")
                link = f"{site_url}/tool/{slug}"
                if desc:
                    lines.append(f"- [{name}]({link}): {desc}")
                else:
                    lines.append(f"- [{name}]({link})")

            lines.append("")
            lines.append("## Categories")
            lines.append("")
            lines.append(f"- [All Tools]({site_url}/tools): complete directory of every free tool")
            lines.append(f"- [Student Hub & Exam Calculators]({site_url}/student-tools): CBSE/university CGPA, negative marking, passing marks, typing test & exam age tools")
            hub_categories = getattr(settings, "HUB_CATEGORIES", ["calculators", "developer-tools", "business-tools", "image-tools"])
            for hub in hub_categories:
                if hub == "pdf-tools":
                    continue
                lines.append(f"- [{hub}]({site_url}/{hub})")

            lines.append("")
            lines.append("## Guides")
            lines.append("")
            lines.append(f"- [Blog]({site_url}/blog): step-by-step guides for every free tool")
            for post in BlogService().get_all():
                lines.append(f"- [{post.title}]({site_url}/blog/{post.pillar}/{post.slug})")

            lines.append("")
            lines.append(f"Sitemap: {site_url}/sitemap.xml")

            content = "\n".join(lines)
            self._llms_cache = (now, content)
            return content
