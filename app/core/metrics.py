import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.log import get_logger

logger = get_logger(__name__)

request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

request_latency = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

active_requests = Gauge(
    "http_requests_active",
    "Number of active HTTP requests",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        active_requests.inc()
        start = time.monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            elapsed = time.monotonic() - start
            active_requests.dec()
            request_count.labels(method=request.method, path=request.url.path, status=status).inc()
            request_latency.labels(method=request.method, path=request.url.path).observe(elapsed)
