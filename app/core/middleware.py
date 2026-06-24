import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.log import get_request_id_filter


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        get_request_id_filter().set_request_id(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


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
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://static.cloudflareinsights.com https://www.googletagmanager.com https://pagead2.googlesyndication.com https://partner.googleadservices.com https://adservice.google.com https://googleads.g.doubleclick.net https://www.google-analytics.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https://pagead2.googlesyndication.com https://www.google.com https://googleads.g.doubleclick.net https://www.google-analytics.com; "
            "connect-src 'self' http://localhost:* https://cloudflareinsights.com https://www.google-analytics.com https://analytics.google.com https://pagead2.googlesyndication.com https://googleads.g.doubleclick.net; "
            "frame-src 'self' https://googleads.g.doubleclick.net https://tpc.googlesyndication.com https://www.google.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response
