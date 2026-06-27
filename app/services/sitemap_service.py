import datetime
import os
import time

from app.core.config import Settings

BASE_URL = "https://www.storybrainai.com"


class SitemapService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._sitemap_cache: tuple[float, str] | None = None
        self._robots_cache: tuple[float, str] | None = None
        self._llms_cache: tuple[float, str] | None = None
        self._cache_ttl = 3600

    def _from_cache(self, cache: tuple[float, str] | None) -> str | None:
        if cache and time.time() - cache[0] < self._cache_ttl:
            return cache[1]
        return None

    def _get_lastmod(self, file_path: str) -> str:
        try:
            full_path = os.path.join(self.settings.base_dir, file_path)
            return datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d")
        except Exception:
            return datetime.datetime.now().strftime("%Y-%m-%d")

    def _get_pri(self, slug: str) -> float:
        tool_priority = {
            "calculator": 0.9, "adsense-calculator": 0.9, "age-calculator": 0.9, "percentage-calculator": 0.9,
            "scientific-calculator": 0.9, "profit-margin-calculator": 0.9,
            "gst-calculator": 0.9, "emi-calculator": 0.9, "compound-calculator": 0.9,
            "mrr-calculator": 0.9, "cac-calculator": 0.9, "burn-rate-calculator": 0.9,
            "salary-calculator": 0.9, "sip-calculator": 0.9, "fd-calculator": 0.9,
            "loan-affordability-calculator": 0.9, "mortgage-overpayment-calculator": 0.9,
            "credit-utilization-calculator": 0.9,
            "debt-calculator": 0.9,
            "date-calculator": 0.9, "eway-bill-calculator": 0.9,
            "youtube-calculator": 0.8, "instagram-calculator": 0.8,
        }
        if slug in tool_priority:
            return tool_priority[slug]
        if slug.startswith("crypto-"):
            return 0.8
        if slug in ("image-compressor", "image-converter",
                     "image-background-remover", "watermark-remover", "meme-generator",
                     "qr-generator", "uuid-generator", "base64-tool",
                       "schema-generator",
                       "sitemap-generator", "robots-txt-generator", "api-tester",
                        "keyword-data-analyzer",
                         "meta-tag-generator",
                         "open-graph-generator"):
            return 0.8
        return 0.7

    def build_sitemap_xml(self) -> str:
        cached = self._from_cache(self._sitemap_cache)
        if cached:
            return cached
        pages = [
            {"url": "/", "file": "templates/index.html", "freq": "weekly", "pri": "1.0"},
        ]

        tools_dir = os.path.join(self.settings.templates_dir, "tools")
        if os.path.exists(tools_dir):
            for f in os.listdir(tools_dir):
                if f.endswith(".html"):
                    tool_name = f[:-5].replace("_", "-")
                    pri = self._get_pri(tool_name)
                    pages.append({
                        "url": f"/tool/{tool_name}",
                        "file": f"templates/tools/{f}",
                        "freq": "daily",
                        "pri": f"{pri:.1f}",
                    })

        pages_dir = os.path.join(self.settings.templates_dir, "pages")
        if os.path.exists(pages_dir):
            for f in os.listdir(pages_dir):
                if f.endswith(".html"):
                    page_name = f[:-5]
                    if page_name in ("privacy", "terms", "disclaimer", "sitemap"):
                        continue
                    pages.append({
                        "url": f"/{page_name}",
                        "file": f"templates/pages/{f}",
                        "freq": "weekly",
                        "pri": "0.4",
                    })

        url_tags = []
        for p in pages:
            lastmod = self._get_lastmod(p["file"])
            url_tags.append(
                f'    <url>\n'
                f'        <loc>{BASE_URL}{p["url"]}</loc>\n'
                f'        <lastmod>{lastmod}</lastmod>\n'
                f'        <changefreq>{p["freq"]}</changefreq>\n'
                f'        <priority>{p["pri"]}</priority>\n'
                f'    </url>'
            )

        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<?xml-stylesheet type="text/xsl" href="/static/sitemap.xsl"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        xml_content += "\n".join(url_tags)
        xml_content += '\n</urlset>'
        self._sitemap_cache = (time.time(), xml_content)
        return xml_content

    def build_robots_txt(self) -> str:
        cached = self._from_cache(self._robots_cache)
        if cached:
            return cached
        result = (
            "# ==========================================\n"
            "# Optimized robots.txt for StoryBrain AI\n"
            "# ==========================================\n\n"
            "# Global Rules\n"
            "User-agent: *\n"
            "Allow: /\n"
            "Allow: /static/\n"
            "Disallow: /api/\n"
            "Disallow: /docs\n"
            "Disallow: /redoc\n"
            "Disallow: /openapi.json\n\n"
            "# Explicitly Allow Major Search Engines\n"
            "User-agent: Googlebot\n"
            "Allow: /\n"
            "Disallow: /api/\n\n"
            "User-agent: Googlebot-Image\n"
            "Allow: /static/\n\n"
            "User-agent: bingbot\n"
            "Allow: /\n"
            "Disallow: /api/\n\n"
            "# Block Resource-Heavy SEO Scrapers\n"
            "User-agent: AhrefsBot\n"
            "Disallow: /\n\n"
            "User-agent: SemrushBot\n"
            "Disallow: /\n\n"
            "User-agent: MJ12bot\n"
            "Disallow: /\n\n"
            "User-agent: DotBot\n"
            "Disallow: /\n\n"
            "User-agent: BLEXBot\n"
            "Disallow: /\n\n"
            "User-agent: PetalBot\n"
            "Disallow: /\n\n"
            "# Explicitly Allow AI Crawlers\n"
            "User-agent: GPTBot\n"
            "Allow: /\n\n"
            "User-agent: ChatGPT-User\n"
            "Allow: /\n\n"
            "User-agent: anthropic-ai\n"
            "Allow: /\n\n"
            "User-agent: Claude-Web\n"
            "Allow: /\n\n"
            "User-agent: Google-Extended\n"
            "Allow: /\n\n"
            f"Sitemap: {BASE_URL}/sitemap.xml\n"
        )
        self._robots_cache = (time.time(), result)
        return result

    def build_llms_txt(self) -> str:
        cached = self._from_cache(self._llms_cache)
        if cached:
            return cached
        txt = ("# StoryBrain AI\n\n"
               "> StoryBrain AI provides a suite of free advanced online tools including SEO generators, "
               "crypto tools, image processing utilities, calculators, and more.\n\n"
               "## Available Tools\n\n")

        tools_dir = os.path.join(self.settings.templates_dir, "tools")
        if os.path.exists(tools_dir):
            tools = [f[:-5] for f in os.listdir(tools_dir) if f.endswith(".html")]
            for t in sorted(tools):
                name = t.replace("_", " ").title()
                slug = t.replace("_", "-")
                txt += f"- [{name}](https://www.storybrainai.com/tool/{slug})\n"

        txt += "\n## Other Pages\n\n"
        pages_dir = os.path.join(self.settings.templates_dir, "pages")
        if os.path.exists(pages_dir):
            pages = [f[:-5] for f in os.listdir(pages_dir) if f.endswith(".html")]
            for p in sorted(pages):
                name = p.replace("-", " ").title()
                txt += f"- [{name}](https://www.storybrainai.com/{p})\n"

        txt += ("\n## Technical Details\n\n"
                "All tools are accessible via the frontend interface. "
                "The `/api/` routes are intended for internal frontend consumption "
                "and are restricted from standard bot access.\n")
        self._llms_cache = (time.time(), txt)
        return txt
