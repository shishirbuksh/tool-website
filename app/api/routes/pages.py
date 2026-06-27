import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.icons import lucide_icon
from app.services.catalog_service import CatalogService
from app.services.seo_service import SeoService

router = APIRouter()
catalog_service = CatalogService(settings)
seo_service = SeoService(settings)

templates = Jinja2Templates(directory=settings.templates_dir)
templates.env.globals["lucide_icon"] = lucide_icon
templates.env.globals["today"] = lambda: datetime.now(UTC).strftime("%Y-%m-%d")

APP_VERSION = uuid.uuid4().hex[:8]
templates.env.globals["app_version"] = APP_VERSION

HUB_CATEGORIES = {
    "ai-tools": ("AI & Crypto", "AI & Crypto Tools — Free Online Predictors & Calculators"),
    "image-tools": ("Image Processing", "Free Online Image Tools — Background Remover, Compressor & Converter"),
    "calculators": ("Calculators", "Free Online Calculators — Math, Finance & Life Calculators"),
    "developer-tools": ("Developer & SEO", "Free Developer & SEO Tools — Schema, Sitemap & Code Generators"),
    "business-tools": ("Business & Operations", "Free Business Tools — Invoice, Orders & Finance Calculators"),
    "pdf-tools": ("Productivity & Utilities", "Free PDF & Productivity Tools — Converter, Password & Trackers"),
}


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/tools", response_class=HTMLResponse)
async def tools_page(request: Request):
    categories, static_pages = catalog_service.get_categorized_tools()
    return templates.TemplateResponse(
        request=request,
        name="tools.html",
        context={"categories": categories, "static_pages": static_pages},
    )


@router.get("/tool/{tool_name}", response_class=HTMLResponse)
async def get_tool(request: Request, tool_name: str):
    if tool_name in ("tools", "sitemap", "offline"):
        raise HTTPException(status_code=404, detail="Not found")
    valid_tools = catalog_service.get_valid_tools()

    if tool_name not in valid_tools:
        raise HTTPException(status_code=404, detail="Tool not found")

    categories, _ = catalog_service.get_categorized_tools()
    seo_data = seo_service.get_seo(tool_name)
    template_name = f"tools/{tool_name.replace('-', '_')}.html"
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "tool_name": tool_name.replace("-", " ").title(),
            "categories": categories,
            "seo_data": seo_data,
        },
    )


@router.get("/sitemap", response_class=HTMLResponse)
async def html_sitemap(request: Request):
    categories, static_pages = catalog_service.get_categorized_tools()
    return templates.TemplateResponse(
        request=request,
        name="pages/sitemap.html",
        context={
            "title": "HTML Sitemap — StoryBrain AI",
            "categories": categories,
            "static_pages": static_pages,
        },
    )


@router.get("/api/tools/catalog")
async def tools_catalog():
    categories, static_pages = catalog_service.get_categorized_tools()
    tools = []
    for cat_name, cat_tools in categories.items():
        for t in cat_tools:
            tools.append({"name": t["name"], "url": t["url"], "desc": t["desc"], "category": cat_name})
    return tools


@router.get("/offline", response_class=HTMLResponse)
async def offline_page(request: Request):
    return templates.TemplateResponse(request=request, name="offline.html")


@router.get("/sw.js", include_in_schema=False)
async def service_worker():
    headers = {"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"}
    return FileResponse(os.path.join(settings.static_dir, "sw.js"), headers=headers)


@router.get("/{page_name}", response_class=HTMLResponse)
async def get_page(request: Request, page_name: str):
    if page_name == "sw.js":
        raise HTTPException(status_code=404, detail="Not found")

    if page_name in HUB_CATEGORIES:
        category_name, seo_title = HUB_CATEGORIES[page_name]
        categories, static_pages = catalog_service.get_categorized_tools()
        hub_tools = categories.get(category_name, [])
        return templates.TemplateResponse(
            request=request,
            name="hub.html",
            context={
                "hub_name": page_name,
                "category_name": category_name,
                "seo_title": seo_title,
                "tools": hub_tools,
                "categories": categories,
                "static_pages": static_pages,
            },
        )

    pages_dir = os.path.join(settings.templates_dir, "pages")
    valid_pages = (
        [f[:-5] for f in os.listdir(pages_dir) if f.endswith(".html")]
        if os.path.exists(pages_dir)
        else []
    )

    if page_name in valid_pages:
        return templates.TemplateResponse(
            request=request,
            name=f"pages/{page_name}.html",
            context={"title": page_name.replace("-", " ").title()},
        )
    raise HTTPException(status_code=404, detail="Page not found")
