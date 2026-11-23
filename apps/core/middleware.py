"""Core Django & ASGI-compatible Middlewares for SEO, Security, and Caching."""

from __future__ import annotations

import os
import re
import secrets
import sys
import uuid
from urllib.parse import urlencode, urlparse
from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect, HttpResponseNotModified
from apps.core.log import reset_request_id, set_request_id

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")
_HSTS = "max-age=31536000; includeSubDomains; preload"
_CSP_BASE = (
    "default-src 'self'; "
    "object-src 'none'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "img-src 'self' data: blob: https://pagead2.googlesyndication.com https://*.googlesyndication.com "
    "https://www.google.com https://www.gstatic.com https://googleads.g.doubleclick.net https://*.doubleclick.net "
    "https://www.google-analytics.com https://*.google-analytics.com https://www.googletagmanager.com "
    "https://ep1.adtrafficquality.google https://ep2.adtrafficquality.google https://*.adtrafficquality.google "
    "https://fundingchoicesmessages.google.com https://*.googleusercontent.com https://*.ggpht.com; "
    "connect-src 'self' https://unpkg.com https://cloudflareinsights.com https://www.google-analytics.com "
    "https://*.google-analytics.com https://analytics.google.com https://www.googletagmanager.com "
    "https://pagead2.googlesyndication.com https://*.googlesyndication.com "
    "https://googleads.g.doubleclick.net https://*.doubleclick.net "
    "https://ep1.adtrafficquality.google https://ep2.adtrafficquality.google https://*.adtrafficquality.google "
    "https://fundingchoicesmessages.google.com https://adservice.google.com https://csi.gstatic.com "
    "https://www.google.com https://cdn.jsdelivr.net https://tessdata.projectnaptha.com; "
    "frame-src 'self' https://googleads.g.doubleclick.net https://*.doubleclick.net "
    "https://tpc.googlesyndication.com https://*.googlesyndication.com https://www.google.com "
    "https://ep1.adtrafficquality.google https://ep2.adtrafficquality.google https://*.adtrafficquality.google "
    "https://fundingchoicesmessages.google.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "worker-src 'self' blob: https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
)
_CSP_SCRIPT_ALLOWED = (
    "'self' https://static.cloudflareinsights.com "
    "https://www.googletagmanager.com https://pagead2.googlesyndication.com https://*.googlesyndication.com "
    "https://partner.googleadservices.com https://adservice.google.com "
    "https://googleads.g.doubleclick.net https://*.doubleclick.net "
    "https://www.google-analytics.com https://*.google-analytics.com "
    "https://ep1.adtrafficquality.google https://ep2.adtrafficquality.google https://*.adtrafficquality.google "
    "https://fundingchoicesmessages.google.com https://www.google.com https://www.gstatic.com "
    "https://unpkg.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net"
)


class Response:
    """Lightweight response mock adapter for async dispatch tests."""
    def __init__(self, content="", status_code=200, headers=None, media_type=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        if media_type:
            self.headers["content-type"] = media_type


class RedirectResponse:
    """Lightweight redirect mock adapter for async dispatch tests."""
    def __init__(self, url: str, status_code: int = 301):
        self.status_code = status_code
        self.headers = {"location": url}
        self.content = b""


class RequestURLAdapter:
    """Compatibility adapter providing .url interface on Django WSGIRequest."""
    __slots__ = ("_request", "path")

    def __init__(self, request):
        self._request = request
        self.path = getattr(request, "path", "/")

    @property
    def query(self) -> str:
        return getattr(self._request, "META", {}).get("QUERY_STRING", "")

    def __str__(self) -> str:
        if hasattr(self._request, "build_absolute_uri"):
            return self._request.build_absolute_uri()
        return self.path

    def __repr__(self) -> str:
        return f"RequestURLAdapter(path={self.path!r})"


class TrustedHostCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_hosts = set(settings.ALLOWED_HOSTS)
        if settings.DEBUG or getattr(settings, "IS_TEST", False) or "test" in os.environ.get("ENV", "").lower() or "pytest" in sys.modules:
            self.allowed_hosts |= {"testserver", "testclient"}

    def __call__(self, request):
        if "*" not in self.allowed_hosts:
            host = request.get_host().split(":")[0].lower()
            if host not in self.allowed_hosts and not any(host.endswith("." + h) for h in self.allowed_hosts if h.startswith(".")):
                return HttpResponse("Invalid Host Header", status=400)
        return self.get_response(request)


class RequestIDMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    async def dispatch(self, request, call_next):
        if not hasattr(request, "url"):
            request.url = RequestURLAdapter(request)
        raw_id = request.headers.get("X-Request-ID", "")
        request_id = raw_id if raw_id and _REQUEST_ID_RE.match(raw_id) else str(uuid.uuid4())
        token = set_request_id(request_id)
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            reset_request_id(token)
            if response is not None:
                response.headers["X-Request-ID"] = request_id

    def __call__(self, request):
        if not hasattr(request, "url"):
            request.url = RequestURLAdapter(request)
        raw_id = request.headers.get("X-Request-ID", "")
        request_id = raw_id if raw_id and _REQUEST_ID_RE.match(raw_id) else str(uuid.uuid4())
        token = set_request_id(request_id)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            reset_request_id(token)


class SecurityHeadersMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    async def dispatch(self, request, call_next):
        nonce = secrets.token_urlsafe(16)
        if hasattr(request, "state"):
            request.state.nonce = nonce
        csp = f"{_CSP_BASE} script-src 'nonce-{nonce}' 'unsafe-eval' {_CSP_SCRIPT_ALLOWED};"
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = _HSTS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        if response.status_code != 304:
            response.headers["Content-Security-Policy"] = csp
        existing_vary = response.headers.get("Vary", "")
        vary_parts = [p.strip() for p in existing_vary.split(",") if p.strip()] if existing_vary else []
        if "Accept-Encoding" not in vary_parts:
            vary_parts.append("Accept-Encoding")
        response.headers["Vary"] = ", ".join(vary_parts)
        if "Content-Language" not in response.headers:
            response.headers["Content-Language"] = "en"
        return response

    def __call__(self, request):
        request.url = RequestURLAdapter(request)
        nonce = secrets.token_urlsafe(16)
        request.nonce = nonce

        response = self.get_response(request)

        csp = f"{_CSP_BASE} script-src 'nonce-{nonce}' 'unsafe-eval' {_CSP_SCRIPT_ALLOWED};"
        response["Strict-Transport-Security"] = _HSTS
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        response["X-Permitted-Cross-Domain-Policies"] = "none"
        if response.status_code != 304:
            response["Content-Security-Policy"] = csp

        if request.path.startswith("/api/"):
            response["X-Robots-Tag"] = "noindex, nofollow"

        origin = request.headers.get("Origin") or request.META.get("HTTP_ORIGIN")
        if origin:
            allowed_origins = getattr(settings, "CORS_ORIGINS", [])
            allowed_hosts = list(settings.ALLOWED_HOSTS)
            allowed = {h.lower() for h in allowed_hosts if h} | {urlparse(o).hostname or "" for o in allowed_origins if o}
            if settings.DEBUG or "*" in settings.ALLOWED_HOSTS:
                allowed |= {"127.0.0.1", "localhost", "testclient"}
            origin_host = (urlparse(origin).hostname or "").lower()
            if origin_host in allowed:
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Credentials"] = "true"
                response["Access-Control-Expose-Headers"] = "X-Request-ID, Content-Length"

        if "X-Request-ID" not in response:
            raw_id = request.headers.get("X-Request-ID") or request.META.get("HTTP_X_REQUEST_ID")
            response["X-Request-ID"] = raw_id if raw_id and _REQUEST_ID_RE.match(raw_id) else str(uuid.uuid4())

        if "Content-Language" not in response:
            response["Content-Language"] = "en"

        return response


class OriginCheckMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response
        self._allowed: set[str] | None = None

    def _get_allowed(self) -> set[str]:
        if self._allowed is None:
            allowed = list(settings.ALLOWED_HOSTS) + [urlparse(o).hostname or "" for o in getattr(settings, "CORS_ORIGINS", [])]
            if settings.DEBUG or "*" in settings.ALLOWED_HOSTS:
                allowed += ["127.0.0.1", "localhost", "testclient"]
            self._allowed = {h.lower() for h in allowed if h}
        return self._allowed

    async def dispatch(self, request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("Origin")
            if origin:
                origin_host = (urlparse(origin).hostname or "").lower()
                if origin_host not in self._get_allowed():
                    from django.http import JsonResponse
                    r = JsonResponse({"detail": "Cross-origin request blocked"}, status=403)
                    # Support Starlette test format
                    r.headers = {"content-type": "application/json"}
                    return r
        return await call_next(request)

    def __call__(self, request):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("Origin")
            if origin:
                origin_host = (urlparse(origin).hostname or "").lower()
                if origin_host not in self._get_allowed():
                    from django.http import JsonResponse
                    return JsonResponse({"detail": "Cross-origin request blocked"}, status=403)
        return self.get_response(request)


class CanonicalHostMiddleware:
    _APEX_HOSTS = {"storybrainai.com"}

    def __init__(self, get_response=None):
        self.get_response = get_response

    async def dispatch(self, request, call_next):
        if request.method in ("GET", "HEAD"):
            host = (request.headers.get("host") or "").split(":")[0].strip().lower()
            if host in self._APEX_HOSTS:

                target = f"https://www.{host}{request.url.path}"
                if request.url.query:
                    target = f"{target}?{request.url.query}"
                return RedirectResponse(url=target, status_code=301)
        return await call_next(request)

    def __call__(self, request):
        if request.method in ("GET", "HEAD"):
            host = request.get_host().split(":")[0].strip().lower()
            if host in self._APEX_HOSTS:
                qs = f"?{request.META['QUERY_STRING']}" if request.META.get("QUERY_STRING") else ""
                target = f"https://www.storybrainai.com{request.path}{qs}"
                return HttpResponsePermanentRedirect(target)
        return self.get_response(request)


class TrailingSlashRedirectMiddleware:
    _LEGACY_PREFIXES = ("/hi", "/es", "/fr", "/de")

    def __init__(self, get_response=None):
        self.get_response = get_response

    async def dispatch(self, request, call_next):
        path = request.url.path
        if (
            request.method in ("GET", "HEAD")
            and len(path) > 1
            and path.endswith("/")
            and not path.lower().startswith("/static/")
        ):
            target = path.rstrip("/").lower() or "/"
            for prefix in self._LEGACY_PREFIXES:
                if target == prefix:
                    target = "/"
                    break
                if target.startswith(f"{prefix}/"):
                    target = target[len(prefix) :] or "/"
                    break
            if request.url.query:
                target = f"{target}?{request.url.query}"
            return RedirectResponse(url=target, status_code=301)
        return await call_next(request)

    def __call__(self, request):
        path = request.path
        if request.method in ("GET", "HEAD") and len(path) > 1 and path.endswith("/") and not path.lower().startswith("/static/"):
            target = path.rstrip("/").lower() or "/"
            for prefix in self._LEGACY_PREFIXES:
                if target == prefix:
                    target = "/"
                    break
                if target.startswith(f"{prefix}/"):
                    target = target[len(prefix):] or "/"
                    break
            qs = f"?{request.META['QUERY_STRING']}" if request.META.get("QUERY_STRING") else ""
            return HttpResponsePermanentRedirect(f"{target}{qs}")
        return self.get_response(request)


class CleanQueryMiddleware:
    _CRAWLER_JUNK = {"pagespeed", "mod_pagespeed"}
    _MARKETING = {"fbclid", "gclid"}
    _MARKETING_PREFIXES = ("utm_",)

    def __init__(self, get_response=None):
        self.get_response = get_response

    async def dispatch(self, request, call_next):
        if request.method in ("GET", "HEAD") and request.url.query:
            params = dict(getattr(request, "query_params", {}))
            junk = {k for k in params if k.lower() in self._CRAWLER_JUNK}
            if getattr(settings, "STRIP_MARKETING_PARAMS", False):
                junk |= {k for k in params if k.lower() in self._MARKETING or k.lower().startswith(self._MARKETING_PREFIXES)}
            if junk:
                clean = {k: v for k, v in params.items() if k not in junk}
                qs = f"?{urlencode(clean)}" if clean else ""

                return RedirectResponse(url=f"{request.url.path}{qs}", status_code=301)
        return await call_next(request)

    def __call__(self, request):
        if request.method in ("GET", "HEAD") and request.GET:
            params = request.GET.dict()
            junk = {k for k in params if k.lower() in self._CRAWLER_JUNK}
            if getattr(settings, "STRIP_MARKETING_PARAMS", False):
                junk |= {k for k in params if k.lower() in self._MARKETING or k.lower().startswith(self._MARKETING_PREFIXES)}
            if junk:
                clean = {k: v for k, v in params.items() if k not in junk}
                qs = f"?{urlencode(clean)}" if clean else ""
                return HttpResponsePermanentRedirect(f"{request.path}{qs}")
        return self.get_response(request)


class CaseSensitiveRedirectMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path != path.lower() and not path.lower().startswith("/static/"):
            target = path.lower()
            if request.url.query:
                target = f"{target}?{request.url.query}"
            return RedirectResponse(url=target, status_code=308)
        return await call_next(request)

    def __call__(self, request):
        path = request.path
        if path != path.lower() and not path.lower().startswith("/static/"):
            target = path.lower()
            qs = f"?{request.META['QUERY_STRING']}" if request.META.get("QUERY_STRING") else ""
            return HttpResponsePermanentRedirect(f"{target}{qs}")
        return self.get_response(request)


class ConditionalGetMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code == 200 and request.method in ("GET", "HEAD"):
            etag = response.get("ETag")
            lm = response.get("Last-Modified")
            if_none_match = request.headers.get("If-None-Match")
            if_modified_since = request.headers.get("If-Modified-Since")
            matched = False
            if etag and if_none_match:
                candidates = [c.strip().strip('W/"').strip('"') for c in if_none_match.split(",")]
                clean_etag = etag.strip('W/"').strip('"')
                if clean_etag in candidates or if_none_match.strip() == etag:
                    matched = True
            elif lm and if_modified_since:
                if if_modified_since.strip() == lm.strip():
                    matched = True

            if matched:
                not_modified = HttpResponseNotModified()
                if etag:
                    not_modified["ETag"] = etag
                if lm:
                    not_modified["Last-Modified"] = lm
                not_modified["Cache-Control"] = response.get("Cache-Control", "public, max-age=0, must-revalidate")
                return not_modified

        return response
