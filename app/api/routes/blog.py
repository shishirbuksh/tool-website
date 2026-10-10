"""Blog HTML endpoints: index, pillar hub, and post pages (mounted BEFORE pages catch-all)."""

import asyncio
import os
import re
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from app.api.routes.pages import NonceJinja2Templates
from app.core.config import settings
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
    t as _tr,
)
from app.core.icons import lucide_icon
from app.core.log import get_logger
from app.core.sanitize import enhance_tables, sanitize_html
from app.services.blog_service import BlogService
from app.services.catalog_service import CatalogService

logger = get_logger(__name__)

__all__ = ["router"]

router = APIRouter()
catalog_service = CatalogService(settings)
blog_service = BlogService(settings)

templates = NonceJinja2Templates(directory=settings.templates_dir)
templates.env.globals["lucide_icon"] = lucide_icon
templates.env.globals["today"] = lambda: datetime.now(UTC).strftime("%Y-%m-%d")
templates.env.globals["SITE_URL"] = settings.SITE_URL.rstrip("/")
templates.env.globals["site_url"] = settings.SITE_URL.rstrip("/")
templates.env.filters["sanitize"] = sanitize_html
templates.env.filters["tables"] = enhance_tables
templates.env.globals["hreflang_links"] = hreflang_links
templates.env.globals["html_lang_for"] = html_lang_for
templates.env.globals["og_locale_for"] = og_locale_for
templates.env.globals["tr"] = _tr
templates.env.globals["normalize_locale"] = normalize_locale
templates.env.globals["supported_locales"] = SUPPORTED_LOCALES
templates.env.globals["locale_meta"] = LOCALE_META
templates.env.globals["localize_path"] = localize_path

APP_VERSION = os.getenv("APP_VERSION", "dev")
templates.env.globals["app_version"] = APP_VERSION

# Panel verdict (Speaker 3): blog is public, no auth/PII. Index/pillar churn
# fast -> short TTL; post is immutable-ish keyed by date_modified + ETag.
# NOTE: HTML carries per-request CSP nonce (SecurityHeadersMiddleware), so
# public edge caching would reuse nonces across users. Use private no-store
# like pages.py to keep nonces single-use.
_INDEX_CACHE_HEADERS = {"Cache-Control": "private, no-cache, no-store, must-revalidate"}
_POST_CACHE_HEADERS = {"Cache-Control": "private, no-cache, no-store, must-revalidate"}
# Back-compat alias for tests importing the old name.
_PAGE_CACHE_HEADERS = _INDEX_CACHE_HEADERS


def _post_etag(pillar: str, slug: str, date_modified: str | None) -> str:
    import hashlib

    raw = f"{pillar}/{slug}:{date_modified or ''}:{APP_VERSION}".encode()
    return '"' + hashlib.sha1(raw).hexdigest()[:32] + '"'


def _not_modified(request: Request, etag: str) -> bool:
    raw = request.headers.get("if-none-match", "")
    if not raw:
        return False
    # Handle W/"...", multiple values, and whitespace per RFC 7232.
    candidates = [v.strip().strip("W").strip().strip('"').strip("'") for v in raw.split(",")]
    clean = etag.strip().strip('"').strip("'")
    return clean in candidates or raw.strip() == etag


_SLUG_RE = re.compile(r"^[a-z0-9-]{1,80}$")


def _assert_safe(value: str) -> str:
    if ".." in value or "/" in value or "\\" in value:
        raise HTTPException(status_code=404, detail="Not found")
    if not _SLUG_RE.match(value or ""):
        raise HTTPException(status_code=404, detail="Not found")
    return value


def _i18n_ctx(bare_path: str, locale: str) -> dict:
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


def _localized_resp(resp, locale: str):
    loc = normalize_locale(locale)
    vary = resp.headers.get("Vary", "")
    if "Accept-Language" not in vary:
        resp.headers["Vary"] = (vary + ", Accept-Language").strip(", ").strip() if vary else "Accept-Language"
    resp.headers["Content-Language"] = loc
    return resp


@router.api_route("/blog", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def blog_index(request: Request) -> HTMLResponse:
    categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
    pillars, posts, recent, popular = await asyncio.gather(
        asyncio.to_thread(blog_service.get_pillars),
        asyncio.to_thread(blog_service.get_all),
        asyncio.to_thread(blog_service.get_recent, 6),
        asyncio.to_thread(blog_service.get_popular, 3),
    )
    # Pillar counts for topic chips (single pass, no extra scans).
    pillar_counts: dict[str, int] = {}
    for p in posts:
        pillar_counts[p.pillar] = pillar_counts.get(p.pillar, 0) + 1
    # Paginate the Latest grid (20/page) to bound DOM/TBT on low-end devices.
    try:
        page = int(request.query_params.get("page", "1"))
    except (TypeError, ValueError):
        page = 1
    per_page = 20
    total_posts = len(posts)
    total_pages = max(1, (total_posts + per_page - 1) // per_page)
    page = min(max(page, 1), total_pages)
    page_posts = posts[(page - 1) * per_page : page * per_page]
    ctx = {
        "title": "Blog",
        "categories": categories,
        "static_pages": static_pages,
        "pillars": pillars,
        "posts": page_posts,
        "total_posts": total_posts,
        "page": page,
        "total_pages": total_pages,
        "per_page": per_page,
        "recent_posts": recent,
        "popular_posts": popular,
        "pillar_counts": pillar_counts,
    }
    ctx.update(_i18n_ctx("/blog", "en"))
    resp = templates.TemplateResponse(request=request, name="blog/index.html", context=ctx)
    resp.headers.update(_INDEX_CACHE_HEADERS)
    return resp


@router.api_route("/hi/blog", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/es/blog", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/fr/blog", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def blog_index_localized(request: Request) -> HTMLResponse:
    loc = normalize_locale(request.url.path.split("/")[1])
    if not is_supported_locale(loc) or loc == "en":
        raise HTTPException(status_code=404, detail="Not found")
    categories, static_pages = await asyncio.to_thread(catalog_service.get_categorized_tools)
    pillars, posts, recent, popular = await asyncio.gather(
        asyncio.to_thread(blog_service.get_pillars),
        asyncio.to_thread(blog_service.get_all, loc),
        asyncio.to_thread(blog_service.get_recent, 6, loc),
        asyncio.to_thread(blog_service.get_popular, 3, loc),
    )
    pillar_counts: dict[str, int] = {}
    for p in posts:
        pillar_counts[p.pillar] = pillar_counts.get(p.pillar, 0) + 1
    try:
        page = int(request.query_params.get("page", "1"))
    except (TypeError, ValueError):
        page = 1
    per_page = 20
    total_posts = len(posts)
    total_pages = max(1, (total_posts + per_page - 1) // per_page)
    page = min(max(page, 1), total_pages)
    page_posts = posts[(page - 1) * per_page : page * per_page]
    ctx = {
        "title": "Blog",
        "categories": categories,
        "static_pages": static_pages,
        "pillars": pillars,
        "posts": page_posts,
        "total_posts": total_posts,
        "page": page,
        "total_pages": total_pages,
        "per_page": per_page,
        "recent_posts": recent,
        "popular_posts": popular,
        "pillar_counts": pillar_counts,
    }
    ctx.update(_i18n_ctx("/blog", loc))
    resp = templates.TemplateResponse(request=request, name="blog/index.html", context=ctx)
    resp.headers.update(_INDEX_CACHE_HEADERS)
    return _localized_resp(resp, loc)


@router.api_route("/blog/{pillar}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def blog_pillar(request: Request, pillar: str) -> HTMLResponse:
    _assert_safe(pillar)
    posts, pillars, cat_static = await asyncio.gather(
        asyncio.to_thread(blog_service.get_by_pillar, pillar),
        asyncio.to_thread(blog_service.get_pillars),
        asyncio.to_thread(catalog_service.get_categorized_tools),
    )
    if not posts and pillar not in pillars:
        raise HTTPException(status_code=404, detail="Pillar not found")
    categories, static_pages = cat_static
    # Tools covered by this pillar (chips linking post→tool, max 12, order-stable).
    seen: list[str] = []
    for p in posts:
        for t in p.tools:
            if t not in seen:
                seen.append(t)
            if len(seen) >= 12:
                break
        if len(seen) >= 12:
            break
    ctx = {
        "title": pillar.replace("-", " ").title(),
        "pillar": pillar,
        "posts": posts,
        "pillars": pillars,
        "pillar_tools": seen,
        "categories": categories,
        "static_pages": static_pages,
    }
    ctx.update(_i18n_ctx(f"/blog/{pillar}", "en"))
    resp = templates.TemplateResponse(request=request, name="blog/pillar.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/hi/blog/{pillar}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/es/blog/{pillar}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/fr/blog/{pillar}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def blog_pillar_localized(request: Request, pillar: str) -> HTMLResponse:
    loc = normalize_locale(request.url.path.split("/")[1])
    if not is_supported_locale(loc) or loc == "en":
        raise HTTPException(status_code=404, detail="Not found")
    _assert_safe(pillar)
    posts, pillars, cat_static = await asyncio.gather(
        asyncio.to_thread(blog_service.get_by_pillar, pillar, loc),
        asyncio.to_thread(blog_service.get_pillars),
        asyncio.to_thread(catalog_service.get_categorized_tools),
    )
    if not posts and pillar not in pillars:
        raise HTTPException(status_code=404, detail="Pillar not found")
    categories, static_pages = cat_static
    seen: list[str] = []
    for p in posts:
        for t in p.tools:
            if t not in seen:
                seen.append(t)
            if len(seen) >= 12:
                break
        if len(seen) >= 12:
            break
    ctx = {
        "title": pillar.replace("-", " ").title(),
        "pillar": pillar,
        "posts": posts,
        "pillars": pillars,
        "pillar_tools": seen,
        "categories": categories,
        "static_pages": static_pages,
    }
    ctx.update(_i18n_ctx(f"/blog/{pillar}", loc))
    resp = templates.TemplateResponse(request=request, name="blog/pillar.html", context=ctx)
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return _localized_resp(resp, loc)


async def _render_blog_post(request: Request, pillar: str, cluster: str, locale: str = "en") -> HTMLResponse:
    loc = normalize_locale(locale)
    _assert_safe(pillar)
    _assert_safe(cluster)
    post, cat_static, pillars = await asyncio.gather(
        asyncio.to_thread(blog_service.get, cluster, loc),
        asyncio.to_thread(catalog_service.get_categorized_tools),
        asyncio.to_thread(blog_service.get_pillars),
    )
    if post is None or post.pillar != pillar:
        raise HTTPException(status_code=404, detail="Post not found")
    categories, static_pages = cat_static
    sibling_posts = await asyncio.to_thread(blog_service.get_by_pillar, pillar, loc)
    related = await asyncio.to_thread(_related_for_post, post, sibling_posts, loc)
    prev_post, next_post = _prev_next(sibling_posts, post.slug)
    # Slug → display name for related-tool cards (single pass over catalog).
    tool_names: dict[str, str] = {}
    for tools in categories.values():
        for t in tools:
            url = str(t.get("url", ""))
            if url.startswith("/tool/"):
                tool_names[url[6:]] = str(t.get("name", ""))
    ctx = {
        "title": post.title,
        "pillar": pillar,
        "post": post,
        "related_posts": related,
        "prev_post": prev_post,
        "next_post": next_post,
        "tool_names": tool_names,
        "pillars": pillars,
        "categories": categories,
        "static_pages": static_pages,
    }
    ctx.update(_i18n_ctx(f"/blog/{pillar}/{cluster}", loc))
    resp = templates.TemplateResponse(request=request, name="blog/post.html", context=ctx)
    resp.headers.update(_POST_CACHE_HEADERS)
    etag = _post_etag(pillar, post.slug, (post.date_modified or "") + loc)
    resp.headers["ETag"] = etag
    if _not_modified(request, etag):
        # 304 must have an empty body (raising HTTPException renders JSON).
        return Response(status_code=304, headers={"ETag": etag, **_POST_CACHE_HEADERS})
    return _localized_resp(resp, loc) if loc != "en" else resp


@router.api_route("/blog/{pillar}/{cluster}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def blog_post(request: Request, pillar: str, cluster: str) -> HTMLResponse:
    return await _render_blog_post(request, pillar, cluster, locale="en")


@router.api_route("/hi/blog/{pillar}/{cluster}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/es/blog/{pillar}/{cluster}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/fr/blog/{pillar}/{cluster}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def blog_post_localized(request: Request, pillar: str, cluster: str) -> HTMLResponse:
    loc = normalize_locale(request.url.path.split("/")[1])
    if not is_supported_locale(loc) or loc == "en":
        raise HTTPException(status_code=404, detail="Not found")
    return await _render_blog_post(request, pillar, cluster, locale=loc)


def _related_for_post(post, sibling_posts: list, locale: str = "en") -> list:
    related = [blog_service.get(s, locale) for s in post.related_posts]
    related = [p for p in related if p is not None]
    if not related:
        related = [p for p in sibling_posts if p.slug != post.slug][:3]
    return related


def _prev_next(sibling_posts: list, slug: str) -> tuple:
    ordered = sorted(sibling_posts, key=lambda p: (p.date_published or "", p.slug))
    idx = next((i for i, p in enumerate(ordered) if p.slug == slug), None)
    if idx is None:
        return None, None
    prev_p = ordered[idx - 1] if idx > 0 else None
    next_p = ordered[idx + 1] if idx + 1 < len(ordered) else None
    return prev_p, next_p
