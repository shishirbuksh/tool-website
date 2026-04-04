import os
import datetime
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings

router = APIRouter()

# Templates setup
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html"
    )

@router.get("/tool/{tool_name}", response_class=HTMLResponse)
async def get_tool(request: Request, tool_name: str):
    tools_dir = os.path.join(settings.TEMPLATES_DIR, "tools")
    valid_tools = []
    if os.path.exists(tools_dir):
        valid_tools = [f[:-5].replace('_', '-') for f in os.listdir(tools_dir) if f.endswith('.html')]
        
    if tool_name not in valid_tools:
        return HTMLResponse(status_code=404, content="Tool not found")
    
    template_name = f"tools/{tool_name.replace('-', '_')}.html"
    return templates.TemplateResponse(
        request=request, 
        name=template_name, 
        context={"tool_name": tool_name.replace('-', ' ').title()}
    )

@router.get("/sitemap.xml")
async def sitemap():
    base_url = "https://storybrainai.com"
    
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
                pages.append({"url": f"/tool/{tool_name}", "file": f"templates/tools/{f}", "freq": "monthly", "pri": "0.8"})
    
    # Dynamically inject static pages
    pages_dir = os.path.join(settings.TEMPLATES_DIR, "pages")
    if os.path.exists(pages_dir):
        for f in os.listdir(pages_dir):
            if f.endswith(".html"):
                page_name = f[:-5]
                # Lower priority for generic static pages like privacy, terms, disclaimer
                pri = "0.2" if page_name in ["privacy", "terms", "disclaimer"] else "0.4"
                pages.append({"url": f"/{page_name}", "file": f"templates/pages/{f}", "freq": "yearly", "pri": pri})
    
    url_tags = []
    for p in pages:
        lastmod = get_lastmod(p["file"])
        url_tags.append(f'    <url><loc>{base_url}{p["url"]}</loc><lastmod>{lastmod}</lastmod><changefreq>{p["freq"]}</changefreq><priority>{p["pri"]}</priority></url>')
        
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<?xml-stylesheet type="text/xsl" href="/static/sitemap.xsl"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml_content += "\n".join(url_tags)
    xml_content += '\n</urlset>'
    
    return Response(content=xml_content, media_type="application/xml")

@router.get("/robots.txt")
async def robots():
    txt = "User-agent: *\nAllow: /\n\nSitemap: https://storybrainai.com/sitemap.xml"
    return Response(content=txt, media_type="text/plain")

@router.get("/{page_name}", response_class=HTMLResponse)
async def get_page(request: Request, page_name: str):
    pages_dir = os.path.join(settings.TEMPLATES_DIR, "pages")
    valid_pages = [f[:-5] for f in os.listdir(pages_dir) if f.endswith('.html')] if os.path.exists(pages_dir) else []
    
    if page_name in valid_pages:
        return templates.TemplateResponse(request=request, name=f"pages/{page_name}.html", context={"title": page_name.title()})
    return HTMLResponse(status_code=404, content="Page not found")
