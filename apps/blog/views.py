"""Blog Views: Index, Pillar listing, and Post detail."""

from __future__ import annotations

import hashlib
from datetime import datetime, UTC
from email.utils import formatdate
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from apps.blog.services import BlogService
from apps.catalog.services import CatalogService

_blog_service = BlogService()
_catalog_service = CatalogService()

_QUARANTINED_POSTS = {
    "love-calculator-explained-fun",
    "crypto-price-prediction-how-it-works",
    "meme-coin-detector-guide",
    "meme-coin-red-flags-learn-guide",
    "airdrop-finder-guide",
}


def _page_canonical(bare_path: str, page: int) -> str:
    base = getattr(settings, "SITE_URL", "https://www.storybrainai.com").rstrip("/")
    url = base + bare_path
    return f"{url}?page={page}" if page > 1 else url


def _post_etag(pillar: str, slug: str, date_modified: str | None) -> str:
    raw = f"{pillar}/{slug}:{date_modified or ''}:{settings.APP_VERSION}".encode()
    return 'W/"' + hashlib.sha1(raw).hexdigest()[:32] + '"'


def blog_index(request):
    categories, static_pages = _catalog_service.get_categorized_tools()
    posts = _blog_service.get_all()
    pillars = sorted({p.pillar for p in posts if p.pillar})
    recent = posts[:6]
    popular = _blog_service.get_popular(3)
    pillar_counts: dict[str, int] = {}
    for p in posts:
        pillar_counts[p.pillar] = pillar_counts.get(p.pillar, 0) + 1

    page_param = request.GET.get("page")
    try:
        page = int(page_param) if page_param is not None else 1
        if page < 1:
            raise Http404("Invalid page")
    except ValueError:
        raise Http404("Invalid page")

    per_page = 20
    total_posts = len(posts)
    total_pages = max(1, (total_posts + per_page - 1) // per_page)
    if page > total_pages:
        raise Http404("Page not found")
    page_posts = posts[(page - 1) * per_page : page * per_page]

    ctx = {
        "title": "Blog",
        "blog_title": "Blog",
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
        "pillar_labels": {p: p.replace("-", " ").title() for p in pillars},
        "locale": "en",
        "html_lang": "en",
        "og_locale": "en_US",
        "bare_path": "/blog",
        "page_canonical": _page_canonical("/blog", page),
        "nonce": getattr(request, "nonce", ""),
    }
    response = render(request, "blog/index.html", ctx)
    response["Cache-Control"] = "public, max-age=0, must-revalidate"
    return response


def blog_pillar(request, pillar: str):
    posts = _blog_service.get_by_pillar(pillar)
    pillars = _blog_service.get_pillars()
    if not posts and not any(p["slug"] == pillar for p in pillars):
        raise Http404("Pillar not found")

    categories, static_pages = _catalog_service.get_categorized_tools()
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
        "plabel": pillar.replace("-", " ").title(),
        "blog_title": "Blog",
        "pillar": pillar,
        "posts": posts,
        "pillars": [p["slug"] for p in pillars],
        "pillar_tools": seen,
        "categories": categories,
        "static_pages": static_pages,
        "locale": "en",
        "html_lang": "en",
        "og_locale": "en_US",
        "bare_path": f"/blog/{pillar}",
        "nonce": getattr(request, "nonce", ""),
    }
    response = render(request, "blog/pillar.html", ctx)
    response["Cache-Control"] = "public, max-age=0, must-revalidate"
    return response


def blog_post(request, pillar: str, cluster: str):
    post = _blog_service.get_post(pillar, cluster)
    if post is None:
        raise Http404("Post not found")

    categories, static_pages = _catalog_service.get_categorized_tools()
    pillars = [p["slug"] for p in _blog_service.get_pillars()]
    sibling_posts = _blog_service.get_by_pillar(pillar)

    # Related posts
    related = [p for p in sibling_posts if p.slug != post.slug][:3]
    ordered = sorted(sibling_posts, key=lambda p: (p.date_published or "", p.slug))
    idx = next((i for i, p in enumerate(ordered) if p.slug == post.slug), None)
    prev_post = ordered[idx - 1] if idx and idx > 0 else None
    next_post = ordered[idx + 1] if idx is not None and idx + 1 < len(ordered) else None

    tool_names: dict[str, str] = {}
    for tools in categories.values():
        for t in tools:
            url = str(t.get("url", ""))
            slug = url.split("/tool/")[-1] if "/tool/" in url else ""
            if slug and "/" not in slug:
                tool_names[slug] = str(t.get("name", ""))

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
        "locale": "en",
        "html_lang": "en",
        "og_locale": "en_US",
        "bare_path": f"/blog/{pillar}/{cluster}",
        "robots_noindex": post.slug in _QUARANTINED_POSTS,
        "nonce": getattr(request, "nonce", ""),
    }

    etag = _post_etag(pillar, post.slug, post.date_modified)
    response = render(request, "blog/post.html", ctx)
    response["Cache-Control"] = "public, max-age=0, must-revalidate"
    response["ETag"] = etag
    if post.date_modified:
        try:
            dt = datetime.strptime(post.date_modified.strip(), "%Y-%m-%d").replace(tzinfo=UTC)
            response["Last-Modified"] = formatdate(dt.timestamp(), usegmt=True)
        except Exception:
            pass
    return response
