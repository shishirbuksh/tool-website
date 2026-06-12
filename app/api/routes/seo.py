import os
import datetime
from fastapi import APIRouter, Response, Request
from app.core.config import settings

router = APIRouter()

BASE_URL = "https://www.storybrainai.com"

@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    def get_lastmod(file_path: str) -> str:
        try:
            full_path = os.path.join(settings.BASE_DIR, file_path)
            return datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d")
        except:
            return datetime.datetime.now().strftime("%Y-%m-%d")

    pages = [
        {"url": "/", "file": "templates/index.html", "freq": "weekly", "pri": "1.0"},
    ]
    
    # Dynamically inject tools
    tools_dir = os.path.join(settings.TEMPLATES_DIR, "tools")
    if os.path.exists(tools_dir):
        for f in os.listdir(tools_dir):
            if f.endswith(".html"):
                tool_name = f[:-5].replace('_', '-')
                pages.append({"url": f"/tool/{tool_name}", "file": f"templates/tools/{f}", "freq": "daily", "pri": "0.9"})
    
    # Dynamically inject static pages
    pages_dir = os.path.join(settings.TEMPLATES_DIR, "pages")
    if os.path.exists(pages_dir):
        for f in os.listdir(pages_dir):
            if f.endswith(".html"):
                page_name = f[:-5]
                # Lower priority for generic static pages like privacy, terms, disclaimer
                pri = "0.2" if page_name in ["privacy", "terms", "disclaimer"] else "0.4"
                pages.append({"url": f"/{page_name}", "file": f"templates/pages/{f}", "freq": "weekly", "pri": pri})
    
    url_tags = []
    for p in pages:
        lastmod = get_lastmod(p["file"])
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
    
    return Response(content=xml_content, media_type="application/xml")

@router.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    content = f"""# ==========================================
# Optimized robots.txt for StoryBrain AI
# ==========================================

# Global Rules
User-agent: *
Allow: /
Allow: /static/
Disallow: /api/
Disallow: /docs
Disallow: /redoc
Disallow: /openapi.json

# Explicitly Allow Major Search Engines
User-agent: Googlebot
Allow: /
Disallow: /api/

User-agent: Googlebot-Image
Allow: /static/

User-agent: bingbot
Allow: /
Disallow: /api/

# Block Resource-Heavy SEO Scrapers
User-agent: AhrefsBot
Disallow: /

User-agent: SemrushBot
Disallow: /

User-agent: MJ12bot
Disallow: /

User-agent: DotBot
Disallow: /

User-agent: BLEXBot
Disallow: /

User-agent: PetalBot
Disallow: /

# Explicitly Allow AI Crawlers
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: Google-Extended
Allow: /

# Sitemaps and AI Context
Sitemap: {BASE_URL}/sitemap.xml
# AI crawlers can read our structured data at:
# {BASE_URL}/llms.txt
"""
    return Response(content=content, media_type="text/plain")

@router.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    txt = "# StoryBrain AI\n\n> StoryBrain AI provides a suite of free advanced online tools including SEO generators, crypto tools, image processing utilities, calculators, and more.\n\n## Available Tools\n\n"
    
    tools_dir = os.path.join(settings.TEMPLATES_DIR, "tools")
    if os.path.exists(tools_dir):
        tools = [f[:-5] for f in os.listdir(tools_dir) if f.endswith(".html")]
        for t in sorted(tools):
            name = t.replace('_', ' ').title()
            slug = t.replace('_', '-')
            txt += f"- [{name}](https://www.storybrainai.com/tool/{slug})\n"
            
    txt += "\n## Other Pages\n\n"
    pages_dir = os.path.join(settings.TEMPLATES_DIR, "pages")
    if os.path.exists(pages_dir):
        pages = [f[:-5] for f in os.listdir(pages_dir) if f.endswith(".html")]
        for p in sorted(pages):
            name = p.replace('-', ' ').title()
            txt += f"- [{name}](https://www.storybrainai.com/{p})\n"
            
    txt += "\n## Technical Details\n\n"
    txt += "All tools are accessible via the frontend interface. The `/api/` routes are intended for internal frontend consumption and are restricted from standard bot access.\n"
    
    return Response(content=txt, media_type="text/plain")
