"""Blog HTML endpoints: index, pillar hub, and post pages (mounted BEFORE pages catch-all)."""

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
templates.env.filters["sanitize"] = lambda html: Markup(nh3.clean(html or ""))

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
    categories, static_pages = catalog_service.get_categorized_tools()
    pillars = blog_service.get_pillars()
    posts = blog_service.get_all()
    resp = templates.TemplateResponse(
        request=request,
        name="blog/index.html",
        context={
            "title": "Blog",
            "categories": categories,
            "static_pages": static_pages,
            "pillars": pillars,
            "posts": posts,
        },
    )
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp


@router.api_route("/blog/{pillar}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def blog_pillar(request: Request, pillar: str) -> HTMLResponse:
    _assert_safe(pillar)
    posts = blog_service.get_by_pillar(pillar)
    if not posts and pillar not in blog_service.get_pillars():
        raise HTTPException(status_code=404, detail="Pillar not found")
    categories, static_pages = catalog_service.get_categorized_tools()
    resp = templates.TemplateResponse(
        request=request,
        name="blog/pillar.html",
        context={
            "title": pillar.replace("-", " ").title(),
            "pillar": pillar,
            "posts": posts,
            "pillars": blog_service.get_pillars(),
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
    post = blog_service.get(cluster)
    if post is None or post.pillar != pillar:
        raise HTTPException(status_code=404, detail="Post not found")
    categories, static_pages = catalog_service.get_categorized_tools()
    related = [p for p in (blog_service.get(s) for s in post.related_posts) if p is not None]
    if not related:
        related = [p for p in blog_service.get_by_pillar(pillar) if p.slug != post.slug][:3]
    resp = templates.TemplateResponse(
        request=request,
        name="blog/post.html",
        context={
            "title": post.title,
            "pillar": pillar,
            "post": post,
            "related_posts": related,
            "pillars": blog_service.get_pillars(),
            "categories": categories,
            "static_pages": static_pages,
        },
    )
    resp.headers.update(_PAGE_CACHE_HEADERS)
    return resp
