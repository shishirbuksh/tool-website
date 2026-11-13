"""HTML page endpoints: home, tools directory, individual tools, hub pages, sitemap, offline, service worker."""

import asyncio
import os
import re
import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from jinja2.exceptions import TemplateNotFound
from pydantic import BaseModel, Field, ValidationError

from app.core.sanitize import sanitize_html
from app.core.tool_data import ToolDataLoader

try:
    import email_validator  # noqa: F401
    from pydantic import EmailStr

    _EmailType = EmailStr
except ImportError:  # email-validator not installed: fall back to plain str
    _EmailType = str  # type: ignore[assignment]

from app.core.config import APP_CSS_HREF, APP_VERSION, settings
from app.core.icons import lucide_icon
from app.core.log import get_logger
from app.core.responses import cached_json
from app.services.blog_service import BlogService
from app.services.catalog_service import CatalogService
from app.services.seo_service import SeoService

logger = get_logger(__name__)

__all__ = ["router"]


class NonceJinja2Templates(Jinja2Templates):
    def TemplateResponse(  # noqa: N802 - overrides Jinja2Templates.TemplateResponse
        self, request, name, context=None, status_code=200, headers=None, media_type=None, background=None
    ):
        if context is None:
            context = {}
        context.setdefault("nonce", getattr(request.state, "nonce", ""))
        context.setdefault("tool_count", len(ToolDataLoader.get_slugs()))
        return super().TemplateResponse(request, name, context, status_code, headers, media_type, background)


class ContactForm(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: _EmailType = Field(..., max_length=254)  # type: ignore[valid-type]
    message: str = Field(..., min_length=1, max_length=5000)
    website: str = Field(default="", max_length=200)
    honeypot: str = Field(default="", max_length=200)


class ContactResponse(BaseModel):
    status: str = Field(default="ok", description="Status of contact form submission")


def _get_contact_recipient() -> str:
    try:
        val = (settings.CONTACT_EMAIL or "").strip()
        if val:
            return val
    except Exception:
        pass
    return os.getenv("CONTACT_EMAIL", "").strip()


_CONTACT_MAX_BYTES = 32_000

_CONTACT_EMAIL_WINDOWS: dict[str, list[float]] = {}
_CONTACT_EMAIL_LOCK = __import__("threading").Lock()

router = APIRouter()
catalog_service = CatalogService(settings)
blog_service = BlogService(settings)
seo_service = SeoService(settings)

templates = NonceJinja2Templates(directory=settings.templates_dir)
templates.env.globals["lucide_icon"] = lucide_icon
templates.env.globals["today"] = lambda: datetime.now(UTC).strftime("%Y-%m-%d")
templates.env.globals["SITE_URL"] = settings.SITE_URL.rstrip("/")
templates.env.globals["site_url"] = settings.SITE_URL.rstrip("/")
templates.env.filters["sanitize"] = sanitize_html

templates.env.globals["app_version"] = APP_VERSION
templates.env.globals["app_css_href"] = APP_CSS_HREF
templates.env.globals["adsense_blog_slot_id"] = settings.ADSENSE_BLOG_SLOT_ID.strip()
templates.env.globals["adsense_tool_slot_id"] = settings.ADSENSE_TOOL_SLOT_ID.strip()

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
        _pages_dir_cache = [
            f[:-5] for f in os.listdir(pages_dir) if f.endswith(".html") and f[:-5] not in {"404", "500", "offline"}
        ]
    else:
        _pages_dir_cache = []
    _pages_dir_cache_ts = now
    return _pages_dir_cache


# ── Legacy Locale 301 Redirects (preserve backlinks & bookmarks) ───────────────
@router.api_route("/hi/{rest_path:path}", methods=["GET", "HEAD"], response_class=RedirectResponse)
@router.api_route("/es/{rest_path:path}", methods=["GET", "HEAD"], response_class=RedirectResponse)
@router.api_route("/fr/{rest_path:path}", methods=["GET", "HEAD"], response_class=RedirectResponse)
@router.api_route("/de/{rest_path:path}", methods=["GET", "HEAD"], response_class=RedirectResponse)
async def legacy_locale_redirect(request: Request, rest_path: str = "") -> RedirectResponse:
    clean = "/" + rest_path.lstrip("/")
    if request.url.query:
        clean = f"{clean}?{request.url.query}"
    return RedirectResponse(url=clean, status_code=301)


@router.api_route("/hi", methods=["GET", "HEAD"], response_class=RedirectResponse)
@router.api_route("/es", methods=["GET", "HEAD"], response_class=RedirectResponse)
@router.api_route("/fr", methods=["GET", "HEAD"], response_class=RedirectResponse)
@router.api_route("/de", methods=["GET", "HEAD"], response_class=RedirectResponse)
async def legacy_locale_root_redirect(request: Request) -> RedirectResponse:
    target = f"/?{request.url.query}" if request.url.query else "/"
    return RedirectResponse(url=target, status_code=301)


@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
    recent_posts, popular_posts, pillars = await asyncio.gather(
        asyncio.to_thread(blog_service.get_recent, 3),
        asyncio.to_thread(blog_service.get_popular, 3),
        asyncio.to_thread(blog_service.get_pillars),
    )
    ctx = {
        "categories": categories,
        "static_pages": static_pages,
        "recent_posts": recent_posts,
        "popular_posts": popular_posts,
        "pillars": pillars,
    }
    ctx.update(_page_context("/"))
    resp = templates.TemplateResponse(request=request, name="index.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    resp.headers["Content-Language"] = "en"
    return resp


@router.api_route("/tools", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def tools_page(request: Request) -> HTMLResponse:
    categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
    ctx = {"categories": categories, "static_pages": static_pages}
    ctx.update(_page_context("/tools"))
    resp = templates.TemplateResponse(request=request, name="pages/tools.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    resp.headers["Content-Language"] = "en"
    return resp


@router.api_route("/directory", methods=["GET", "HEAD"], response_class=RedirectResponse)
async def directory_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(url="/tools", status_code=301)


@router.api_route("/offline", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def offline_page(request: Request) -> HTMLResponse:
    categories, _ = await asyncio.to_thread(catalog_service.get_categorized_tools)
    ctx = {"categories": categories}
    ctx.update(_page_context("/offline"))
    ctx["robots_noindex"] = True
    resp = templates.TemplateResponse(request=request, name="pages/offline.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    resp.headers["X-Robots-Tag"] = "noindex, follow"
    resp.headers["Content-Language"] = "en"
    return resp


@router.api_route("/sitemap", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def html_sitemap(request: Request) -> HTMLResponse:
    categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
    pillars, blog_posts = await asyncio.gather(
        asyncio.to_thread(blog_service.get_pillars),
        asyncio.to_thread(blog_service.get_all),
    )
    ctx = {
        "title": "HTML Sitemap — StoryBrain AI",
        "categories": categories,
        "static_pages": static_pages,
        "pillars": pillars,
        "blog_posts": blog_posts,
    }
    ctx.update(_page_context("/sitemap"))
    resp = templates.TemplateResponse(request=request, name="pages/sitemap.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    resp.headers["Content-Language"] = "en"
    return resp


@router.api_route("/api/tools/catalog", methods=["GET", "HEAD"], response_class=Response)
async def tools_catalog(request: Request) -> Response:
    try:
        categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
        tools = []
        for cat_name, cat_tools in categories.items():
            for t in cat_tools:
                tools.append(
                    {"name": t["name"], "url": t["url"], "desc": t["desc"], "category": cat_name}
                )
        resp = cached_json(tools, max_age=300, stale_while_revalidate=3600)
        resp.headers["Content-Language"] = "en"
        return resp
    except Exception as e:
        logger.exception("Failed to generate tools catalog")
        raise HTTPException(status_code=500, detail="Failed to generate catalog") from e


@router.post("/api/contact", response_model=ContactResponse)
async def contact_submission(request: Request) -> ContactResponse:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > _CONTACT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None
    try:
        if len(str(body)) > _CONTACT_MAX_BYTES:
            raise HTTPException(status_code=413, detail="Payload too large")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body") from None
    try:
        form = ContactForm(**body)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body") from None
    if (form.website or "").strip() or (form.honeypot or "").strip():
        logger.warning("Contact honeypot tripped — dropping spam")
        return ContactResponse(status="ok")
    if not form.name.strip() or not str(form.email).strip() or not form.message.strip():
        raise HTTPException(status_code=400, detail="All fields are required")

    safe_name = re.sub(r"[\r\n]+", " ", form.name).strip()
    safe_email = str(form.email).replace("\r", "").replace("\n", "").strip()
    safe_message_snippet = form.message.replace("\r", " ").replace("\n", " ")
    safe_name = re.sub(r"[\x00-\x1f\x7f]", "", safe_name)
    safe_message_snippet = re.sub(r"[\x00-\x1f\x7f]", "", safe_message_snippet)
    logger.info("Contact form submission from %s (%s): %.80s", safe_name, safe_email, safe_message_snippet)

    now = time.time()
    with _CONTACT_EMAIL_LOCK:
        bucket = _CONTACT_EMAIL_WINDOWS.setdefault(safe_email.lower(), [])
        while bucket and bucket[0] < now - 60:
            bucket.pop(0)
        if len(bucket) >= 3:
            raise HTTPException(status_code=429, detail="Too many messages from this address")
        bucket.append(now)
        if len(_CONTACT_EMAIL_WINDOWS) > 2000:
            cutoff = now - 60
            for key in list(_CONTACT_EMAIL_WINDOWS):
                window = _CONTACT_EMAIL_WINDOWS.get(key)
                if not window or window[-1] < cutoff:
                    _CONTACT_EMAIL_WINDOWS.pop(key, None)

    contact_recipient = _get_contact_recipient()
    if not contact_recipient:
        if settings.is_prod:
            logger.error("Contact form dropped: CONTACT_EMAIL not configured in prod")
            raise HTTPException(
                status_code=503,
                detail="Contact is temporarily unavailable. Please email hello@storybrainai.com directly.",
            )
        logger.warning("Contact form received but CONTACT_EMAIL not configured — queued without email (dev only)")
        return ContactResponse(status="ok")

    if contact_recipient:
        try:
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg.set_content(f"Name: {safe_name}\nEmail: {safe_email}\n\nMessage:\n{form.message}")
            msg["Subject"] = f"Contact form: {safe_name}"
            msg["From"] = contact_recipient or "noreply@localhost"
            msg["To"] = contact_recipient
            msg["Reply-To"] = safe_email
            smtp_host = settings.SMTP_HOST or os.getenv("SMTP_HOST", "localhost")
            smtp_port = int(settings.SMTP_PORT or os.getenv("SMTP_PORT", "25"))
            smtp_user = settings.SMTP_USER or os.getenv("SMTP_USER", "")
            smtp_pass = settings.SMTP_PASS or os.getenv("SMTP_PASS", "")

            def _send_mail() -> None:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                    try:
                        s.starttls()
                    except Exception as e:
                        is_local = smtp_host in ("localhost", "127.0.0.1", "::1")
                        if settings.is_prod or not is_local or smtp_user:
                            raise RuntimeError("Mail TLS required") from e
                    if smtp_user and smtp_pass:
                        s.login(smtp_user, smtp_pass)
                    s.send_message(msg)

            try:
                await asyncio.to_thread(_send_mail)
            except RuntimeError as e:
                raise HTTPException(status_code=502, detail="Mail TLS required") from e
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Failed to email contact form: %s", e)
            raise HTTPException(status_code=502, detail="Failed to send message") from e

    return ContactResponse(status="ok")


def _tool_etag(tool_name: str, date_modified: str | None) -> str:
    import hashlib

    raw = f"tool/{tool_name}:{date_modified or ''}:{APP_VERSION}".encode()
    return '"' + hashlib.sha1(raw).hexdigest()[:32] + '"'


def _normalize_etag(v: str) -> str:
    v = v.strip()
    if v.startswith(("W/", "w/")):
        v = v[2:].strip()
    return v.strip('"').strip("'")


def _not_modified(request: Request, etag: str) -> bool:
    raw = request.headers.get("if-none-match", "")
    if not raw:
        return False
    candidates = {_normalize_etag(v) for v in raw.split(",") if v.strip()}
    clean = _normalize_etag(etag)
    return clean in candidates or raw.strip() == etag


def _page_context(bare_path: str) -> dict:
    return {
        "locale": "en",
        "html_lang": "en",
        "og_locale": "en_US",
        "bare_path": bare_path,
        "robots_noindex": False,
    }


async def _render_tool(request: Request, tool_name: str, locale: str = "en") -> Response:
    if ".." in tool_name or "/" in tool_name or "\\" in tool_name:
        raise HTTPException(status_code=404, detail="Not found")
    if tool_name in ("tools", "sitemap", "offline"):
        raise HTTPException(status_code=404, detail="Not found")
    valid_tools = catalog_service.get_valid_tools()
    if tool_name not in valid_tools:
        raise HTTPException(status_code=404, detail="Tool not found")

    seo_data = seo_service.get_seo(tool_name)
    dmod = seo_data.date_modified if seo_data else None
    etag = _tool_etag(tool_name, dmod)
    if _not_modified(request, etag):
        _h304 = {"ETag": etag, "Content-Language": "en", **_PAGE_CACHE_HEADERS}
        return Response(status_code=304, headers=_h304)

    categories, _ = await asyncio.to_thread(catalog_service.get_categorized_tools)
    related_guides = await asyncio.to_thread(blog_service.get_posts_for_tool, tool_name, 3)

    template_name = f"tools/{tool_name.replace('-', '_')}.html"
    bare_path = f"/tool/{tool_name}"
    ctx = {
        "tool_name": seo_data.name if seo_data else tool_name.replace("-", " ").title(),
        "categories": categories,
        "seo_data": seo_data,
        "related_guides": related_guides,
    }
    ctx.update(_page_context(bare_path))
    try:
        resp = templates.TemplateResponse(request=request, name=template_name, context=ctx)
    except TemplateNotFound:
        raise HTTPException(status_code=404, detail="Tool not found") from None
    resp.headers.update(_PAGE_CACHE_HEADERS)
    resp.headers["ETag"] = etag
    resp.headers["Content-Language"] = "en"
    return resp


@router.api_route("/tool/{tool_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_tool(request: Request, tool_name: str):
    return await _render_tool(request, tool_name, locale="en")


@router.api_route("/{page_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_page(request: Request, page_name: str) -> HTMLResponse:
    if ".." in page_name or "/" in page_name or "\\" in page_name:
        raise HTTPException(status_code=404, detail="Not found")
    if page_name in ("sw.js", "favicon.ico", "404", "500", "offline"):
        raise HTTPException(status_code=404, detail="Not found")

    if page_name == "pdf-tools":
        return RedirectResponse(url="/productivity-tools", status_code=301)

    if page_name in settings.HUB_CATEGORIES:
        category_name, seo_title = settings.HUB_CATEGORIES[page_name]
        categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
        hub_tools = categories.get(category_name, [])
        try:
            ctx = {
                "hub_name": page_name,
                "category_name": category_name,
                "seo_title": seo_title,
                "title": seo_title or category_name,
                "tools": hub_tools,
                "categories": categories,
                "static_pages": static_pages,
            }
            ctx.update(_page_context(f"/{page_name}"))
            resp = templates.TemplateResponse(request=request, name="hub.html", context=ctx)
            resp.headers.update(_PAGE_CACHE_HEADERS)
            resp.headers["Content-Language"] = "en"
            return resp
        except Exception as e:
            logger.exception("Failed to render hub template for %s", page_name)
            raise HTTPException(status_code=500, detail="Failed to render hub page") from e

    if page_name in _get_cached_page_names():
        categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
        try:
            ctx = {
                "title": page_name.replace("-", " ").title(),
                "categories": categories,
                "static_pages": static_pages,
            }
            ctx.update(_page_context(f"/{page_name}"))
            resp = templates.TemplateResponse(request=request, name=f"pages/{page_name}.html", context=ctx)
            resp.headers.update(_PAGE_CACHE_HEADERS)
            resp.headers["Content-Language"] = "en"
            return resp
        except Exception as e:
            logger.exception("Failed to render page template for %s", page_name)
            raise HTTPException(status_code=500, detail="Failed to render page") from e

    raise HTTPException(status_code=404, detail="Page not found")
