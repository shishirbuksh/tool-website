"""ASGI middleware: request ID propagation, origin-based CSRF, security headers, rate limiting."""

import asyncio
import secrets
import time
import uuid
from collections import defaultdict
from urllib.parse import urlparse

from starlette.datastructures import URL
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.log import reset_request_id, set_request_id

_HSTS = "max-age=31536000; includeSubDomains; preload"
_CSP = (
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
    def __init__(self, app):
        super().__init__(app)
        self._allowed: set[str] | None = None

    def _get_allowed(self) -> set[str]:
        if self._allowed is None:
            allowed = settings.allowed_hosts_list + [
                url.hostname for url in map(URL, settings.cors_origins_list)
            ]
            self._allowed = {h for h in allowed if h}
        return self._allowed

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
        nonce = secrets.token_urlsafe(16)
        request.state.nonce = nonce
        csp = _CSP.replace("'unsafe-inline'", f"'nonce-{nonce}' 'unsafe-inline'", 1)
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = _HSTS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        response.headers["Content-Security-Policy"] = csp
        response.headers["Vary"] = "Accept-Encoding"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter for non-GET requests.

    IP resolution priority:
      1. X-Real-IP   — set by Caddy, authoritative (can't be spoofed by client)
      2. Rightmost X-Forwarded-For token — appended by the outermost trusted proxy
      3. ASGI client.host  — direct connection without proxy

    State backend:
      - Redis (via app.core.cache) when available: shared across all Gunicorn workers.
      - In-process defaultdict as transparent fallback (single-worker or dev).
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._redis = None
        self._redis_checked = False

    def _get_redis(self):
        if not self._redis_checked:
            self._redis_checked = True
            try:
                from app.core.cache import _get_redis as _redis_conn  # noqa: PLC0415
                self._redis = _redis_conn()
            except Exception:
                self._redis = None
        return self._redis

    @staticmethod
    def _resolve_ip(request: Request) -> str:
        """Return the real client IP, trusting the reverse-proxy headers."""
        # X-Real-IP is set by Caddy to the actual remote addr — authoritative.
        real_ip = request.headers.get("X-Real-IP", "").strip()
        if real_ip:
            return real_ip
        # Fallback: rightmost token in XFF is appended by the outermost trusted proxy.
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            return xff.split(",")[-1].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited_redis(self, redis, key: str, now: float) -> bool:
        """Sliding-window check via Redis sorted set. Returns True if request should be blocked."""
        try:
            pipe = redis.pipeline()
            cutoff = now - 60
            pipe.zremrangebyscore(key, "-inf", cutoff)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, 120)
            results = pipe.execute()
            count = results[2]
            return count > self.requests_per_minute
        except Exception:
            return False  # fail open on Redis errors

    def _is_rate_limited_memory(self, client_ip: str, now: float) -> bool:
        """Sliding-window check against in-process dict."""
        window = self._windows[client_ip]
        cutoff = now - 60
        while window and window[0] < cutoff:
            window.pop(0)
        if len(window) >= self.requests_per_minute:
            return True
        window.append(now)
        return False

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "GET":
            return await call_next(request)

        client_ip = self._resolve_ip(request)
        now = time.time()
        redis = self._get_redis()

        if redis:
            key = f"ratelimit:{client_ip}"
            blocked = await asyncio.get_running_loop().run_in_executor(
                None, self._is_rate_limited_redis, redis, key, now
            )
        else:
            blocked = self._is_rate_limited_memory(client_ip, now)

        if blocked:
            return Response(
                content='{"detail":"Rate limit exceeded. Try again in a minute."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60", "X-RateLimit-Limit": str(self.requests_per_minute)},
            )
        return await call_next(request)


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_size:
                    return Response(
                        content=f'{{"detail":"Request body exceeds {self.max_size // (1024*1024)}MB limit"}}',
                        status_code=413,
                        media_type="application/json",
                    )
            except (ValueError, TypeError):
                return Response(
                    content='{"detail":"Invalid Content-Length header"}',
                    status_code=400,
                    media_type="application/json",
                )
        return await call_next(request)


class CaseSensitiveRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path != path.lower() and not path.startswith("/static/"):
            from starlette.responses import RedirectResponse
            return RedirectResponse(url=str(request.url.replace(path=path.lower())), status_code=301)
        return await call_next(request)


class NoIndexAPIMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response
