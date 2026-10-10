"""HTML page endpoints: home, tools directory, individual tools, hub pages, sitemap, offline, service worker."""

import asyncio
import os
import re
import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from jinja2.exceptions import TemplateNotFound
from pydantic import BaseModel, Field, ValidationError

from app.core.i18n import (
    LOCALE_META,
    SUPPORTED_LOCALES,
    hreflang_links,
    html_lang_for,
    is_supported_locale,
    localize_path,
    normalize_locale,
    og_locale_for,
)
from app.core.i18n import (
    t as tr,
)
from app.core.sanitize import sanitize_html

try:
    import email_validator  # noqa: F401
    from pydantic import EmailStr

    _EmailType = EmailStr
except ImportError:  # email-validator not installed: fall back to plain str
    _EmailType = str  # type: ignore[assignment]

from app.core.config import settings
from app.core.icons import lucide_icon
from app.core.log import get_logger
from app.core.responses import cached_json
from app.services.blog_service import BlogService
from app.services.catalog_service import CatalogService
from app.services.seo_service import SeoService

logger = get_logger(__name__)

CONTACT_RECIPIENT = settings.CONTACT_EMAIL or os.getenv("CONTACT_EMAIL", "")

__all__ = ["router"]


class NonceJinja2Templates(Jinja2Templates):
    def TemplateResponse(  # noqa: N802 - overrides Jinja2Templates.TemplateResponse
        self, request, name, context=None, status_code=200, headers=None, media_type=None, background=None
    ):
        if context is None:
            context = {}
        context.setdefault("nonce", getattr(request.state, "nonce", ""))
        return super().TemplateResponse(request, name, context, status_code, headers, media_type, background)


class ContactForm(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: _EmailType = Field(..., max_length=254)  # type: ignore[valid-type]
    message: str = Field(..., min_length=1, max_length=5000)


class ContactResponse(BaseModel):
    status: str = Field(default="ok", description="Status of contact form submission")


_CONTACT_MAX_BYTES = 32_000

# Per-email contact throttle (spam oracle guard): 3/min per sender address.
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
templates.env.globals["hreflang_links"] = hreflang_links
templates.env.globals["html_lang_for"] = html_lang_for
templates.env.globals["og_locale_for"] = og_locale_for
templates.env.globals["tr"] = tr
templates.env.globals["normalize_locale"] = normalize_locale
templates.env.globals["supported_locales"] = SUPPORTED_LOCALES
templates.env.globals["locale_meta"] = LOCALE_META
templates.env.globals["localize_path"] = localize_path

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
async def home(request: Request) -> HTMLResponse:
    # Sync YAML/dir scans run in a worker thread so the event loop stays free.
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
    ctx.update(_i18n_context("/", "en"))
    resp = templates.TemplateResponse(request=request, name="index.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/hi/", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/es/", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/fr/", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/hi", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/es", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/fr", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def home_localized(request: Request) -> HTMLResponse:
    loc = normalize_locale(request.url.path.split("/")[1])
    if not is_supported_locale(loc) or loc == "en":
        raise HTTPException(status_code=404, detail="Not found")
    categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
    recent_posts, popular_posts, pillars = await asyncio.gather(
        asyncio.to_thread(blog_service.get_recent, 3, loc),
        asyncio.to_thread(blog_service.get_popular, 3, loc),
        asyncio.to_thread(blog_service.get_pillars),
    )
    ctx = {
        "categories": categories,
        "static_pages": static_pages,
        "recent_posts": recent_posts,
        "popular_posts": popular_posts,
        "pillars": pillars,
    }
    ctx.update(_i18n_context("/", loc))
    resp = templates.TemplateResponse(request=request, name="index.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    vary = resp.headers.get("Vary", "")
    if "Accept-Language" not in vary:
        resp.headers["Vary"] = (vary + ", Accept-Language").strip(", ").strip()
    resp.headers["Content-Language"] = loc
    return resp


@router.api_route("/tools", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def tools_page(request: Request) -> HTMLResponse:
    categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
    ctx = {"categories": categories, "static_pages": static_pages}
    ctx.update(_i18n_context("/tools", "en"))
    resp = templates.TemplateResponse(request=request, name="pages/tools.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/hi/tools", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/es/tools", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/fr/tools", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def tools_page_localized(request: Request) -> HTMLResponse:
    loc = normalize_locale(request.url.path.split("/")[1])
    if not is_supported_locale(loc) or loc == "en":
        raise HTTPException(status_code=404, detail="Not found")
    categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
    ctx = {"categories": categories, "static_pages": static_pages}
    ctx.update(_i18n_context("/tools", loc))
    resp = templates.TemplateResponse(request=request, name="pages/tools.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    resp.headers["Content-Language"] = loc
    return resp


@router.api_route("/directory", methods=["GET", "HEAD"], response_class=RedirectResponse)
async def directory_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(url="/tools", status_code=301)


@router.api_route("/offline", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def offline_page(request: Request) -> HTMLResponse:
    # Footer (included via base.html) iterates `categories` — pass it like every
    # other page route so /offline never 500s on UndefinedError.
    categories, _ = catalog_service.get_categorized_tools()
    ctx = {"categories": categories}
    ctx.update(_i18n_context("/offline", "en"))
    resp = templates.TemplateResponse(request=request, name="pages/offline.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/sitemap", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def html_sitemap(request: Request) -> HTMLResponse:
    categories, static_pages = catalog_service.get_categorized_tools()
    ctx = {
        "title": "HTML Sitemap — StoryBrain AI",
        "categories": categories,
        "static_pages": static_pages,
        "pillars": blog_service.get_pillars(),
        "blog_posts": blog_service.get_all(),
    }
    ctx.update(_i18n_context("/sitemap", "en"))
    resp = templates.TemplateResponse(request=request, name="pages/sitemap.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/api/tools/catalog", methods=["GET", "HEAD"], response_class=Response)
async def tools_catalog(request: Request) -> Response:
    try:
        loc = normalize_locale(request.query_params.get("lang", "en"))
        if loc == "en" or not is_supported_locale(loc):
            categories, static_pages = catalog_service.get_categorized_tools()
        else:
            categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools_localized, loc)
        tools = []
        for cat_name, cat_tools in categories.items():
            for t in cat_tools:
                tools.append({"name": t["name"], "url": t["url"], "desc": t["desc"], "category": cat_name})
        resp = cached_json(tools, max_age=300, stale_while_revalidate=3600)
        if loc != "en":
            resp.headers["Content-Language"] = loc
        return resp
    except Exception as e:
        logger.exception("Failed to generate tools catalog")
        raise HTTPException(status_code=500, detail="Failed to generate catalog") from e


@router.api_route("/sw.js", methods=["GET", "HEAD"], response_class=FileResponse, include_in_schema=False)
async def service_worker() -> FileResponse:
    headers = {
        "Service-Worker-Allowed": "/",
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }
    sw_path = os.path.join(settings.static_dir, "sw.js")
    if not os.path.isfile(sw_path):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(sw_path, headers=headers)


@router.post("/api/contact", response_model=ContactResponse)
async def contact_submission(request: Request) -> ContactResponse:
    # TODO: add honeypot field + Turnstile/CAPTCHA verification to block contact spam bots.
    # Size check via Content-Length to reject oversized payloads early.
    # NOTE: Content-Length can be missing (chunked) — enforce again after parsing.
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > _CONTACT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None
    # Chunked/no-header bypass guard: measure actual parsed size (bounded by MaxBody 10MB).
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
    if not form.name.strip() or not str(form.email).strip() or not form.message.strip():
        raise HTTPException(status_code=400, detail="All fields are required")

    # Strip newlines from name to prevent header/log injection.
    safe_name = re.sub(r"[\r\n]+", " ", form.name).strip()
    safe_email = str(form.email).replace("\r", "").replace("\n", "").strip()
    safe_message_snippet = form.message.replace("\r", " ").replace("\n", " ")
    # Sanitize ANSI/log injection: strip control chars except space.
    safe_name = re.sub(r"[\x00-\x1f\x7f]", "", safe_name)
    safe_message_snippet = re.sub(r"[\x00-\x1f\x7f]", "", safe_message_snippet)
    logger.info("Contact form submission from %s (%s): %.80s", safe_name, safe_email, safe_message_snippet)

    # Per-sender throttle (in addition to global RateLimitMiddleware 60/min).
    now = time.time()
    with _CONTACT_EMAIL_LOCK:
        bucket = _CONTACT_EMAIL_WINDOWS.setdefault(safe_email.lower(), [])
        while bucket and bucket[0] < now - 60:
            bucket.pop(0)
        if len(bucket) >= 3:
            raise HTTPException(status_code=429, detail="Too many messages from this address")
        bucket.append(now)
        # Bound memory against email rotation: prune stale senders past 2000 keys.
        if len(_CONTACT_EMAIL_WINDOWS) > 2000:
            cutoff = now - 60
            for key in list(_CONTACT_EMAIL_WINDOWS):
                window = _CONTACT_EMAIL_WINDOWS.get(key)
                if not window or window[-1] < cutoff:
                    _CONTACT_EMAIL_WINDOWS.pop(key, None)

    if not CONTACT_RECIPIENT:
        logger.warning("Contact form received but CONTACT_EMAIL not configured — queued without email")
        return ContactResponse(status="ok")

    if CONTACT_RECIPIENT:
        try:
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg.set_content(f"Name: {safe_name}\nEmail: {safe_email}\n\nMessage:\n{form.message}")
            msg["Subject"] = f"Contact form: {safe_name}"
            # Fixed From to avoid SPF spoofing; user address goes in Reply-To.
            msg["From"] = CONTACT_RECIPIENT or "noreply@localhost"
            msg["To"] = CONTACT_RECIPIENT
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
                        # Fail closed: plaintext allowed only for local relay in dev.
                        is_local = smtp_host in ("localhost", "127.0.0.1", "::1")
                        if settings.is_prod or not is_local or smtp_user:
                            raise RuntimeError("Mail TLS required") from e
                    if smtp_user and smtp_pass:
                        s.login(smtp_user, smtp_pass)
                    s.send_message(msg)

            # SMTP is blocking — offload to worker thread so event loop stays free.
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


def _i18n_context(bare_path: str, locale: str) -> dict:
    loc = normalize_locale(locale)
    base = settings.SITE_URL.rstrip("/")
    return {
        "locale": loc,
        "html_lang": html_lang_for(loc),
        "og_locale": og_locale_for(loc),
        "hreflangs": hreflang_links(settings.SITE_URL, bare_path),
        "bare_path": bare_path,
        "locale_urls": {code: base + localize_path(bare_path, code) for code in SUPPORTED_LOCALES},
    }


async def _render_tool(request: Request, tool_name: str, locale: str = "en") -> HTMLResponse:
    loc = normalize_locale(locale)
    if ".." in tool_name or "/" in tool_name or "\\" in tool_name:
        raise HTTPException(status_code=404, detail="Not found")
    if tool_name in ("tools", "sitemap", "offline"):
        raise HTTPException(status_code=404, detail="Not found")
    valid_tools = catalog_service.get_valid_tools()
    if tool_name not in valid_tools:
        raise HTTPException(status_code=404, detail="Tool not found")
    categories, _ = catalog_service.get_categorized_tools()
    seo_data = seo_service.get_seo(tool_name, locale=loc)
    template_name = f"tools/{tool_name.replace('-', '_')}.html"
    bare_path = f"/tool/{tool_name}"
    ctx = {
        "tool_name": seo_data.name,
        "categories": categories,
        "seo_data": seo_data,
    }
    ctx.update(_i18n_context(bare_path, loc))
    try:
        resp = templates.TemplateResponse(request=request, name=template_name, context=ctx)
    except TemplateNotFound:
        raise HTTPException(status_code=404, detail="Tool not found") from None
    resp.headers.update(_PAGE_CACHE_HEADERS)
    # Vary on language so CDN/edge caches keep locale variants separate.
    vary = resp.headers.get("Vary", "")
    if "Accept-Language" not in vary:
        resp.headers["Vary"] = (vary + ", Accept-Language").strip(", ").strip()
    resp.headers["Content-Language"] = loc
    return resp


@router.api_route("/tool/{tool_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_tool(request: Request, tool_name: str):
    return await _render_tool(request, tool_name, locale="en")


@router.api_route("/hi/tool/{tool_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/es/tool/{tool_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/fr/tool/{tool_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_tool_localized(request: Request, tool_name: str):
    loc = normalize_locale(request.url.path.split("/")[1])
    if not is_supported_locale(loc) or loc == "en":
        raise HTTPException(status_code=404, detail="Not found")
    return await _render_tool(request, tool_name, locale=loc)


@router.api_route("/hi/{page_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/es/{page_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/fr/{page_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_page_localized(request: Request, page_name: str) -> HTMLResponse:
    loc = normalize_locale(request.url.path.split("/")[1])
    if not is_supported_locale(loc) or loc == "en":
        raise HTTPException(status_code=404, detail="Not found")
    if ".." in page_name or "/" in page_name or "\\" in page_name:
        raise HTTPException(status_code=404, detail="Not found")
    if page_name in ("sw.js", "favicon.ico", "sitemap", "offline"):
        raise HTTPException(status_code=404, detail="Not found")
    if page_name == "pdf-tools":
        return RedirectResponse(url=f"/{loc}/productivity-tools", status_code=301)
    if page_name in settings.HUB_CATEGORIES:
        category_name, seo_title = settings.HUB_CATEGORIES[page_name]
        categories, static_pages = catalog_service.get_categorized_tools()
        hub_tools = categories.get(category_name, [])
        ctx = {
            "hub_name": page_name,
            "category_name": category_name,
            "seo_title": seo_title,
            "title": seo_title or category_name,
            "tools": hub_tools,
            "categories": categories,
            "static_pages": static_pages,
        }
        ctx.update(_i18n_context(f"/{page_name}", loc))
        resp = templates.TemplateResponse(request=request, name="hub.html", context=ctx)
        resp.headers.update(_PAGE_CACHE_HEADERS)
        resp.headers["Content-Language"] = loc
        return resp
    if page_name in _get_cached_page_names():
        categories, static_pages = catalog_service.get_categorized_tools()
        ctx = {
            "title": page_name.replace("-", " ").title(),
            "categories": categories,
            "static_pages": static_pages,
        }
        ctx.update(_i18n_context(f"/{page_name}", loc))
        resp = templates.TemplateResponse(request=request, name=f"pages/{page_name}.html", context=ctx)
        resp.headers.update(_PAGE_CACHE_HEADERS)
        resp.headers["Content-Language"] = loc
        return resp
    raise HTTPException(status_code=404, detail="Page not found")


@router.api_route("/{page_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_page(request: Request, page_name: str) -> HTMLResponse:
    if ".." in page_name or "/" in page_name or "\\" in page_name:
        raise HTTPException(status_code=404, detail="Not found")
    if page_name in ("sw.js", "favicon.ico"):
        raise HTTPException(status_code=404, detail="Not found")

    # Legacy hub alias: /pdf-tools -> /productivity-tools (301, preserves SEO equity).
    if page_name == "pdf-tools":
        return RedirectResponse(url="/productivity-tools", status_code=301)

    if page_name in settings.HUB_CATEGORIES:
        category_name, seo_title = settings.HUB_CATEGORIES[page_name]
        categories, static_pages = catalog_service.get_categorized_tools()
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
            ctx.update(_i18n_context(f"/{page_name}", "en"))
            resp = templates.TemplateResponse(request=request, name="hub.html", context=ctx)
            resp.headers.update(_PAGE_CACHE_HEADERS)
            return resp
        except Exception as e:
            logger.exception("Failed to render hub template for %s", page_name)
            raise HTTPException(status_code=500, detail="Failed to render hub page") from e

    if page_name in _get_cached_page_names():
        categories, static_pages = catalog_service.get_categorized_tools()
        try:
            ctx = {
                "title": page_name.replace("-", " ").title(),
                "categories": categories,
                "static_pages": static_pages,
            }
            ctx.update(_i18n_context(f"/{page_name}", "en"))
            resp = templates.TemplateResponse(request=request, name=f"pages/{page_name}.html", context=ctx)
            resp.headers.update(_PAGE_CACHE_HEADERS)
            return resp
        except Exception as e:
            logger.exception("Failed to render page template for %s", page_name)
            raise HTTPException(status_code=500, detail="Failed to render page") from e
    raise HTTPException(status_code=404, detail="Page not found")
