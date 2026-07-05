import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.log import get_logger

logger = get_logger(__name__)

_PATH_CARDINALITY_WARNED: set[str] = set()

def _safe_path_label(request, max_labels: int = 100) -> str:
    """Return the route pattern path to bound Prometheus label cardinality.
    
    Falls back to a truncated raw path when no route is matched, and warns
    once per unknown path pattern.
    """
    route = request.scope.get("route")
    if route is not None:
        return getattr(route, "path", request.url.path)
    path = request.url.path
    if len(_PATH_CARDINALITY_WARNED) < max_labels and path not in _PATH_CARDINALITY_WARNED:
        _PATH_CARDINALITY_WARNED.add(path)
    return path

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
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed = time.monotonic() - start
            status = response.status_code if response is not None else 500
            active_requests.dec()
            path = _safe_path_label(request)
            request_count.labels(method=request.method, path=path, status=status).inc()
            request_latency.labels(method=request.method, path=path).observe(elapsed)
