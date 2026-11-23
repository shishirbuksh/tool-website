"""Catalog Views: Home, Tools directory, Tool detail, Hub categories, and Static pages."""

from __future__ import annotations

import os
import re
import time
from email.utils import formatdate
from datetime import datetime, UTC
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import render
from apps.catalog.services import CatalogService, SeoService, ToolDataLoader, tool_etag
from apps.blog.services import BlogService

_catalog_service = CatalogService()
_seo_service = SeoService()
_blog_service = BlogService()

_QUARANTINED_TOOLS = {
    "love-calculator",
    "crypto-price-prediction",
    "meme-coin-detector",
    "airdrop-finder",
    "crypto-scam-checker",
    "crypto-red-flag-self-assessment-tool",
}


def _page_context(request, bare_path: str) -> dict:
    return {
        "request": request,
        "locale": "en",
        "html_lang": "en",
        "og_locale": "en_US",
        "bare_path": bare_path,
        "robots_noindex": False,
        "nonce": getattr(request, "nonce", ""),
        "tool_count": len(ToolDataLoader.get_slugs()),
    }


def home(request):
    categories, static_pages = _catalog_service.get_categorized_tools()
    recent_posts = _blog_service.get_recent(3)
    popular_posts = _blog_service.get_popular(3)
    pillars = _blog_service.get_pillars()

    ctx = {
        "categories": categories,
        "static_pages": static_pages,
        "recent_posts": recent_posts,
        "popular_posts": popular_posts,
        "pillars": pillars,
    }
    ctx.update(_page_context(request, "/"))
    response = render(request, "index.html", ctx)
    response["Cache-Control"] = "public, max-age=0, must-revalidate"
    return response


def tools_page(request):
    categories, static_pages = _catalog_service.get_categorized_tools()
    ctx = {"categories": categories, "static_pages": static_pages}
    ctx.update(_page_context(request, "/tools"))
    response = render(request, "pages/tools.html", ctx)
    response["Cache-Control"] = "public, max-age=0, must-revalidate"
    return response


def directory_redirect(request):
    return HttpResponsePermanentRedirect("/tools")


def tool_detail(request, tool_name: str):
    if tool_name == "crypto-red-flag-self-assessment-tool":
        tool_name = "crypto-scam-checker"

    if ".." in tool_name or "/" in tool_name or "\\" in tool_name:
        raise Http404("Invalid tool name")
    if tool_name in ("tools", "sitemap", "offline"):
        raise Http404("Tool not found")

    valid_tools = _catalog_service.get_valid_tools()
    if tool_name not in valid_tools:
        raise Http404("Tool not found")

    seo_data = _seo_service.get_seo(tool_name)
    dmod = seo_data.date_modified if seo_data else None
    etag = tool_etag(tool_name, dmod)

    template_name = f"tools/{tool_name.replace('-', '_')}.html"
    categories, _ = _catalog_service.get_categorized_tools()
    related_guides = _blog_service.get_posts_for_tool(tool_name, 3)

    tool_raw = ToolDataLoader.get(tool_name) or {}
    tool_category = tool_raw.get("category", "")
    hub_links = {
        "AI & Crypto": "/ai-tools",
        "Image Processing": "/image-tools",
        "Calculators": "/calculators",
        "Developer & SEO": "/developer-tools",
        "Business & Operations": "/business-tools",
        "Productivity & Utilities": "/productivity-tools",
    }
    hub_url = hub_links.get(tool_category, "/tools")

    ctx = {
        "tool_name": seo_data.name if seo_data else tool_name.replace("-", " ").title(),
        "tool_slug": tool_name,
        "tool_category": tool_category,
        "hub_url": hub_url,
        "categories": categories,
        "seo_data": seo_data,
        "related_guides": related_guides,
    }
    ctx.update(_page_context(request, f"/tool/{tool_name}"))
    if tool_name in _QUARANTINED_TOOLS:
        ctx["robots_noindex"] = True

    try:
        response = render(request, template_name, ctx)
    except Exception as e:
        raise Http404("Tool template not found") from e

    response["Cache-Control"] = "public, max-age=0, must-revalidate"
    response["ETag"] = etag
    if dmod:
        try:
            dt = datetime.strptime(dmod.strip(), "%Y-%m-%d").replace(tzinfo=UTC)
            response["Last-Modified"] = formatdate(dt.timestamp(), usegmt=True)
        except Exception:
            pass

    return response


def hub_or_page(request, page_name: str):
    if ".." in page_name or "/" in page_name or "\\" in page_name:
        raise Http404("Invalid page")
    if page_name in ("sw.js", "favicon.ico", "404", "500"):
        raise Http404("Page not found")

    if page_name == "pdf-tools":
        return HttpResponsePermanentRedirect("/productivity-tools")

    hub_categories = getattr(settings, "HUB_CATEGORIES", {})
    categories, static_pages = _catalog_service.get_categorized_tools()

    if page_name in hub_categories:
        category_name, seo_title = hub_categories[page_name]
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
        ctx.update(_page_context(request, f"/{page_name}"))
        tpl = f"pages/{page_name}.html" if os.path.isfile(os.path.join(settings.BASE_DIR, "templates", "pages", f"{page_name}.html")) else "hub.html"
        response = render(request, tpl, ctx)
        response["Cache-Control"] = "public, max-age=0, must-revalidate"
        return response

    _page_aliases = {
        "privacy-policy": "privacy",
        "terms-of-service": "terms",
        "student-hub": "student-tools",
    }
    canonical_name = _page_aliases.get(page_name, page_name)

    pages_dir = os.path.join(settings.BASE_DIR, "templates", "pages")
    resolved_path = os.path.join(pages_dir, f"{canonical_name}.html")

    if os.path.isfile(resolved_path):
        ctx = {
            "title": canonical_name.replace("-", " ").title(),
            "categories": categories,
            "static_pages": static_pages,
        }
        ctx.update(_page_context(request, f"/{page_name}"))
        if page_name == "offline":
            ctx["robots_noindex"] = True
        response = render(request, f"pages/{canonical_name}.html", ctx)
        response["Cache-Control"] = "public, max-age=0, must-revalidate"
        if page_name == "offline":
            response["X-Robots-Tag"] = "noindex, follow"
        return response

    raise Http404(f"Page {page_name} not found")


def legacy_locale_redirect(request, rest_path: str = ""):
    clean = "/" + rest_path.lstrip("/")
    if len(clean) > 1 and clean.endswith("/"):
        clean = clean.rstrip("/")
    qs = f"?{request.META['QUERY_STRING']}" if request.META.get("QUERY_STRING") else ""
    return HttpResponsePermanentRedirect(f"{clean}{qs}")


def tools_catalog_api(request):
    categories, _ = _catalog_service.get_categorized_tools()
    tools = []
    for cat_name, cat_tools in categories.items():
        for t in cat_tools:
            tools.append({"name": t["name"], "url": t["url"], "desc": t["desc"], "category": cat_name})
    response = JsonResponse(tools, safe=False)
    response["Cache-Control"] = "public, max-age=300, stale-while-revalidate=3600"
    return response


def contact_submission(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    import json
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)

    name = str(body.get("name", "")).strip()
    email = str(body.get("email", "")).strip()
    message = str(body.get("message", "")).strip()
    website = str(body.get("website", "")).strip()
    honeypot = str(body.get("honeypot", "")).strip()

    if website or honeypot:
        return JsonResponse({"status": "ok"})
    if not name or not email or "@" not in email or not message:
        return JsonResponse({"detail": "All fields are required"}, status=400)

    return JsonResponse({"status": "ok"})
