"""Blog HTML endpoints: index, pillar hub, and post pages (mounted BEFORE pages catch-all)."""

import asyncio
import os
import re
import time
from datetime import UTC, datetime

import nh3
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from markupsafe import Markup

from app.api.routes.pages import NonceJinja2Templates
from app.core.config import settings
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

APP_VERSION = os.getenv("APP_VERSION", "dev")
templates.env.globals["app_version"] = APP_VERSION

_PAGE_CACHE_HEADERS = {"Cache-Control": "private, no-cache, no-store, must-revalidate"}

_SLUG_RE = re.compile(r"^[a-z0-9-]{1,80}$")


def _assert_safe(value: str) -> str:
    if ".." in value or "/" in value or "\\" in value:
        raise HTTPException(status_code=404, detail="Not found")
    if not _SLUG_RE.match(value or ""):
        raise HTTPException(status_code=404, detail="Not found")
    return value


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
    resp = templates.TemplateResponse(
        request=request,
        name="blog/index.html",
        context={
            "title": "Blog",
            "categories": categories,
            "static_pages": static_pages,
            "pillars": pillars,
            "posts": posts,
            "recent_posts": recent,
            "popular_posts": popular,
            "pillar_counts": pillar_counts,
        },
    )
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


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
    resp = templates.TemplateResponse(
        request=request,
        name="blog/pillar.html",
        context={
            "title": pillar.replace("-", " ").title(),
            "pillar": pillar,
            "posts": posts,
            "pillars": pillars,
            "pillar_tools": seen,
            "categories": categories,
            "static_pages": static_pages,
        },
    )
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/blog/{pillar}/{cluster}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def blog_post(request: Request, pillar: str, cluster: str) -> HTMLResponse:
    _assert_safe(pillar)
    _assert_safe(cluster)
    post, cat_static, pillars = await asyncio.gather(
        asyncio.to_thread(blog_service.get, cluster),
        asyncio.to_thread(catalog_service.get_categorized_tools),
        asyncio.to_thread(blog_service.get_pillars),
    )
    if post is None or post.pillar != pillar:
        raise HTTPException(status_code=404, detail="Post not found")
    categories, static_pages = cat_static
    sibling_posts = await asyncio.to_thread(blog_service.get_by_pillar, pillar)
    related = await asyncio.to_thread(_related_for_post, post, sibling_posts)
    prev_post, next_post = _prev_next(sibling_posts, post.slug)
    # Slug → display name for related-tool cards (single pass over catalog).
    tool_names: dict[str, str] = {}
    for tools in categories.values():
        for t in tools:
            url = str(t.get("url", ""))
            if url.startswith("/tool/"):
                tool_names[url[6:]] = str(t.get("name", ""))
    resp = templates.TemplateResponse(
        request=request,
        name="blog/post.html",
        context={
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
        },
    )
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


def _related_for_post(post, sibling_posts: list) -> list:
    from app.services.blog_service import BlogService  # noqa: PLC0415 (type-only)

    related = [blog_service.get(s) for s in post.related_posts]
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
