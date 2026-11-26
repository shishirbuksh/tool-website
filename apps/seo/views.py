"""SEO Views: Dynamic Sitemap, Robots.txt, llms.txt, and IndexNow."""

from __future__ import annotations

import hmac
import os
import re
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from apps.seo.services import SitemapService

_sitemap_service = SitemapService()
_INDEXNOW_KEY_RE = re.compile(r"^[0-9a-fA-F]{8,128}$")


def sitemap_xml(request):
    content = _sitemap_service.build_sitemap_xml()
    response = HttpResponse(content, content_type="application/xml")
    response["Cache-Control"] = "public, max-age=3600"
    return response


def sitemap_index_xml(request):
    return HttpResponsePermanentRedirect("/sitemap.xml")


def sitemap_locale_xml(request, locale: str):
    if locale.strip().lower() == "en":
        return HttpResponsePermanentRedirect("/sitemap.xml")
    raise Http404("Locale sitemap not found")


def robots_txt(request):
    content = _sitemap_service.build_robots_txt()
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "public, max-age=60, s-maxage=10, must-revalidate"
    return response


def robots_alias(request):
    return HttpResponsePermanentRedirect("/robots.txt")


def llms_txt(request):
    content = _sitemap_service.build_llms_txt()
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "public, max-age=3600"
    return response


def indexnow_key_file(request, key: str):
    expected = getattr(settings, "INDEXNOW_KEY", "").strip() or os.environ.get("INDEXNOW_KEY", "").strip()

    if expected and _INDEXNOW_KEY_RE.match(key) and hmac.compare_digest(key, expected):
        response = HttpResponse(expected, content_type="text/plain; charset=utf-8")
        response["Cache-Control"] = "public, max-age=86400"
        return response
    raise Http404("IndexNow verification key not found")
