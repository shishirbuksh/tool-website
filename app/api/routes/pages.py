"""HTML page endpoints: home, tools directory, individual tools, hub pages, sitemap, offline, service worker."""

import os
import time
from datetime import UTC, datetime

import nh3
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.core.config import settings
from app.core.icons import lucide_icon
from app.core.log import get_logger
from app.core.responses import cached_json, no_cache_json
from app.services.catalog_service import CatalogService
from app.services.seo_service import SeoService

logger = get_logger(__name__)

CONTACT_RECIPIENT = os.getenv("CONTACT_EMAIL", "")

__all__ = ["router"]


class NonceJinja2Templates(Jinja2Templates):
    def TemplateResponse(self, request, name, context=None, status_code=200, headers=None, media_type=None):  # noqa: N802
        if context is None:
            context = {}
        context.setdefault("nonce", getattr(request.state, "nonce", ""))
        return super().TemplateResponse(request, name, context, status_code, headers, media_type)


router = APIRouter()
catalog_service = CatalogService(settings)
seo_service = SeoService(settings)

templates = NonceJinja2Templates(directory=settings.templates_dir)
templates.env.globals["lucide_icon"] = lucide_icon
templates.env.globals["today"] = lambda: datetime.now(UTC).strftime("%Y-%m-%d")
templates.env.filters["sanitize"] = lambda html: Markup(nh3.clean(html or ""))

APP_VERSION = os.getenv("APP_VERSION", "dev")
templates.env.globals["app_version"] = APP_VERSION

# Cache-control: Disable Edge HTML caching to ensure cryptographic CSP Nonce rotates per request.
_PAGE_CACHE_HEADERS = {"Cache-Control": "private, no-cache, no-store, must-revalidate"}

_pages_dir_cache: list[str] | None = None
_pages_dir_cache_ts: float = 0
_PAGES_DIR_TTL = 300


def _get_cached_page_names() -> list[str]:
    global _pages_dir_cache, _pages_dir_cache_ts
    now = time.time()
    if _pages_dir_cache is not None and now - _pages_dir_cache_ts < _PAGES_DIR_TTL:
        return _pages_dir_cache
    pages_dir = os.path.join(settings.templates_dir, "pages")
    if os.path.exists(pages_dir):
        _pages_dir_cache = [f[:-5] for f in os.listdir(pages_dir) if f.endswith(".html")]
    else:
        _pages_dir_cache = []
    _pages_dir_cache_ts = now
    return _pages_dir_cache

@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def home(request: Request):
    resp = templates.TemplateResponse(request=request, name="index.html")
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/tools", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def tools_page(request: Request):
    categories, static_pages = catalog_service.get_categorized_tools()
    resp = templates.TemplateResponse(
        request=request,
        name="tools.html",
        context={"categories": categories, "static_pages": static_pages},
    )
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/tool/{tool_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_tool(request: Request, tool_name: str):
    if ".." in tool_name or "/" in tool_name or "\\" in tool_name:
        raise HTTPException(status_code=404, detail="Not found")
    if tool_name in ("tools", "sitemap", "offline"):
        raise HTTPException(status_code=404, detail="Not found")
    valid_tools = catalog_service.get_valid_tools()

    if tool_name not in valid_tools:
        raise HTTPException(status_code=404, detail="Tool not found")

    categories, _ = catalog_service.get_categorized_tools()
    seo_data = seo_service.get_seo(tool_name)
    template_name = f"tools/{tool_name.replace('-', '_')}.html"
    resp = templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "tool_name": tool_name.replace("-", " ").title(),
            "categories": categories,
            "seo_data": seo_data,
        },
    )
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/sitemap", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def html_sitemap(request: Request):
    categories, static_pages = catalog_service.get_categorized_tools()
    resp = templates.TemplateResponse(
        request=request,
        name="pages/sitemap.html",
        context={
            "title": "HTML Sitemap — StoryBrain AI",
            "categories": categories,
            "static_pages": static_pages,
        },
    )
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/api/tools/catalog", methods=["GET", "HEAD"])
async def tools_catalog():
    categories, static_pages = catalog_service.get_categorized_tools()
    tools = []
    for cat_name, cat_tools in categories.items():
        for t in cat_tools:
            tools.append({"name": t["name"], "url": t["url"], "desc": t["desc"], "category": cat_name})
    return cached_json(tools, max_age=300, stale_while_revalidate=3600)


@router.api_route("/offline", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def offline_page(request: Request):
    resp = templates.TemplateResponse(request=request, name="offline.html")
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/sw.js", methods=["GET", "HEAD"], include_in_schema=False)
async def service_worker():
    headers = {
        "Service-Worker-Allowed": "/",
        "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
    }
    return FileResponse(os.path.join(settings.static_dir, "sw.js"), headers=headers)


@router.post("/api/contact")
async def contact_submission(request: Request):
    from pydantic import BaseModel
    class ContactForm(BaseModel):
        name: str
        email: str
        message: str

    body = await request.json()
    form = ContactForm(**body)
    if not form.name.strip() or not form.email.strip() or not form.message.strip():
        raise HTTPException(status_code=400, detail="All fields are required")

    logger.info("Contact form submission from %s (%s): %.80s", form.name, form.email, form.message)

    if CONTACT_RECIPIENT:
        try:
            import smtplib
            from email.message import EmailMessage
            msg = EmailMessage()
            msg.set_content(f"Name: {form.name}\nEmail: {form.email}\n\nMessage:\n{form.message}")
            msg["Subject"] = f"Contact form: {form.name}"
            msg["From"] = form.email
            msg["To"] = CONTACT_RECIPIENT
            smtp_host = os.getenv("SMTP_HOST", "localhost")
            smtp_port = int(os.getenv("SMTP_PORT", "25"))
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                s.send_message(msg)
        except Exception as e:
            logger.warning("Failed to email contact form: %s", e)

    return {"status": "ok"}


@router.api_route("/{page_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_page(request: Request, page_name: str):
    if ".." in page_name or "/" in page_name:
        raise HTTPException(status_code=404, detail="Not found")
    if page_name in ("sw.js", "favicon.ico"):
        raise HTTPException(status_code=404, detail="Not found")

    if page_name in settings.HUB_CATEGORIES:
        category_name, seo_title = settings.HUB_CATEGORIES[page_name]
        categories, static_pages = catalog_service.get_categorized_tools()
        hub_tools = categories.get(category_name, [])
        resp = templates.TemplateResponse(
            request=request,
            name="hub.html",
            context={
                "hub_name": page_name,
                "category_name": category_name,
                "seo_title": seo_title,
                "title": seo_title or category_name,
                "tools": hub_tools,
                "categories": categories,
                "static_pages": static_pages,
            },
        )
        resp.headers.update(_PAGE_CACHE_HEADERS)
        return resp

    if page_name in _get_cached_page_names():
        resp = templates.TemplateResponse(
            request=request,
            name=f"pages/{page_name}.html",
            context={"title": page_name.replace("-", " ").title()},
        )
        resp.headers.update(_PAGE_CACHE_HEADERS)
        return resp
    raise HTTPException(status_code=404, detail="Page not found")
