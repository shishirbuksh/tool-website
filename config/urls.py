"""Root URL configuration for StoryBrain AI."""

from __future__ import annotations

import os
from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import include, path


def _is_internal(request) -> bool:
    remote_addr = request.META.get("REMOTE_ADDR", "").strip()
    if remote_addr in ("127.0.0.1", "::1"):
        real_ip = (request.headers.get("x-real-ip") or request.META.get("HTTP_X_REAL_IP", "")).strip()
        if real_ip:
            return real_ip in ("127.0.0.1", "::1", "localhost")
        return True
    return False


def healthz(request):
    return JsonResponse({"status": "ok"})


def readyz(request):
    return JsonResponse({"status": "ok"})


def metrics_view(request):
    if not _is_internal(request):
        return HttpResponse("Forbidden", status=403)
    from apps.core.metrics import request_count
    request_count.labels(method="GET", path="/metrics", status=200).inc()
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


def versionz(request):
    return JsonResponse({"version": getattr(settings, "APP_VERSION", "1.0.0")})


def favicon_ico(request):
    path = os.path.join(settings.BASE_DIR, "static", "favicon.ico")
    if os.path.isfile(path):
        response = FileResponse(open(path, "rb"), content_type="image/x-icon")
        response["Cache-Control"] = "public, max-age=604800, stale-while-revalidate=86400"
        return response
    return HttpResponse(status=404)


def apple_touch_icon(request):
    path = os.path.join(settings.BASE_DIR, "static", "apple-touch-icon.png")
    if os.path.isfile(path):
        response = FileResponse(open(path, "rb"), content_type="image/png")
        response["Cache-Control"] = "public, max-age=604800, stale-while-revalidate=86400"
        return response
    return HttpResponse(status=404)


def webmanifest(request):
    path = os.path.join(settings.BASE_DIR, "static", "manifest.json")
    if os.path.isfile(path):
        response = FileResponse(open(path, "rb"), content_type="application/manifest+json")
        response["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
        return response
    return HttpResponse(status=404)


_ADS_TXT_CONTENT = "google.com, pub-6310719489589992, DIRECT, f08c47fec0942fa0\n"


def ads_txt(request):
    candidates = [
        os.path.join(settings.BASE_DIR, "static", "ads.txt"),
        os.path.join(settings.BASE_DIR, "public", "ads.txt"),
        os.path.join(settings.BASE_DIR, "ads.txt"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            response = HttpResponse(content, content_type="text/plain; charset=utf-8")
            response["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
            return response
    response = HttpResponse(_ADS_TXT_CONTENT, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
    return response


def sw_js(request):
    sw_path = os.path.join(settings.BASE_DIR, "static", "sw.js")
    if os.path.isfile(sw_path):
        response = FileResponse(open(sw_path, "rb"), content_type="application/javascript")
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["Service-Worker-Allowed"] = "/"
        return response
    return HttpResponse(status=404)


def handler404_view(request, exception=None):
    from django.shortcuts import render
    from apps.catalog.services import ToolDataLoader
    ctx = {
        "status_code": 404,
        "request": request,
        "nonce": getattr(request, "nonce", ""),
        "bare_path": getattr(request, "path", "/"),
        "tool_count": len(ToolDataLoader.get_slugs()),
    }
    response = render(request, "pages/404.html", ctx, status=404)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def handler500_view(request):
    from django.shortcuts import render
    from apps.catalog.services import ToolDataLoader
    ctx = {
        "status_code": 500,
        "request": request,
        "nonce": getattr(request, "nonce", ""),
        "bare_path": getattr(request, "path", "/"),
        "tool_count": len(ToolDataLoader.get_slugs()),
    }
    response = render(request, "pages/500.html", ctx, status=500)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


handler404 = "config.urls.handler404_view"
handler500 = "config.urls.handler500_view"


urlpatterns = [
    # Health checks & ops
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("versionz", versionz, name="versionz"),
    path("metrics", metrics_view, name="metrics"),

    # Static SEO roots
    path("favicon.ico", favicon_ico, name="favicon_ico"),
    path("apple-touch-icon.png", apple_touch_icon, name="apple_touch_icon"),
    path("apple-touch-icon-precomposed.png", apple_touch_icon, name="apple_touch_icon_precomposed"),
    path("site.webmanifest", webmanifest, name="site_webmanifest"),
    path("manifest.json", webmanifest, name="manifest_json"),
    path("ads.txt", ads_txt, name="ads_txt"),
    path("sw.js", sw_js, name="sw_js"),
    path("static/sw.js", sw_js, name="static_sw_js"),

    # SEO & Sitemaps
    path("", include("apps.seo.urls")),

    # Analytics APIs
    path("", include("apps.analytics.urls")),

    # Tools computation APIs
    path("", include("apps.tools_api.urls")),

    # Blog Engine
    path("", include("apps.blog.urls")),

    # Catalog & Pages (mounted last so it catches dynamic pages and root /)
    path("", include("apps.catalog.urls")),
]

from django.urls import re_path
from django.views.static import serve
urlpatterns += [
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": getattr(settings, "STATIC_DIR", os.path.join(settings.BASE_DIR, "static"))}),
]
