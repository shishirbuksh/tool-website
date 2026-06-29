"""ASGI middleware: request ID propagation, origin-based CSRF, security headers."""

import uuid
from urllib.parse import urlparse

from starlette.datastructures import URL
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.log import set_request_id, reset_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = set_request_id(request_id)
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            reset_request_id(token)
            if response is not None:
                response.headers["X-Request-ID"] = request_id


class OriginCheckMiddleware(BaseHTTPMiddleware):
    _allowed: set[str] | None = None

    @classmethod
    def _get_allowed(cls) -> set[str]:
        if cls._allowed is None:
            allowed = settings.allowed_hosts_list + [
                url.hostname for url in map(URL, settings.cors_origins_list)
            ]
            cls._allowed = {h for h in allowed if h}
        return cls._allowed

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("Origin")
            if origin:
                origin_host = urlparse(origin).hostname or ""
                if origin_host not in self._get_allowed():
                    return Response(
                        content='{"detail":"Cross-origin request blocked"}',
                        status_code=403,
                        media_type="application/json",
                    )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com https://www.googletagmanager.com https://pagead2.googlesyndication.com https://partner.googleadservices.com https://adservice.google.com https://googleads.g.doubleclick.net https://www.google-analytics.com https://ep1.adtrafficquality.google https://ep2.adtrafficquality.google; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "img-src 'self' data: blob: https://pagead2.googlesyndication.com https://www.google.com https://googleads.g.doubleclick.net https://www.google-analytics.com https://ep1.adtrafficquality.google https://ep2.adtrafficquality.google; "
            "connect-src 'self' https://cloudflareinsights.com https://www.google-analytics.com https://analytics.google.com https://pagead2.googlesyndication.com https://googleads.g.doubleclick.net https://ep1.adtrafficquality.google https://ep2.adtrafficquality.google; "
            "frame-src 'self' https://googleads.g.doubleclick.net https://tpc.googlesyndication.com https://www.google.com https://ep1.adtrafficquality.google https://ep2.adtrafficquality.google; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response
