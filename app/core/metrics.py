import re
import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.log import get_logger

logger = get_logger(__name__)

_PATH_CARDINALITY_WARNED: set[str] = set()
_CARDINALITY_CAP_WARNED = False

_UUID_RE = re.compile(
    r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)"
)
_NUMERIC_RE = re.compile(r"/\d+(?=/|$)")
_TOOL_SLUG_RE = re.compile(r"^/tool/[^/]+")
_PAGE_RE = re.compile(r"^/(about|contact|privacy|terms|disclaimer)/?$")


def reset_cardinality() -> None:
    """Reset cardinality tracking state (test helper)."""
    global _CARDINALITY_CAP_WARNED
    _PATH_CARDINALITY_WARNED.clear()
    _CARDINALITY_CAP_WARNED = False


def _normalize_path(path: str) -> str:
    """Bound cardinality: collapse high-cardinality segments to templates."""
    if path.startswith("/static/"):
        return "/static/*"
    if _PAGE_RE.match(path):
        return "/{page}"
    # /tool/<anything> (incl. deeper) -> /tool/{slug}[...]
    if _TOOL_SLUG_RE.match(path):
        path = _TOOL_SLUG_RE.sub("/tool/{slug}", path, count=1)
    path = _UUID_RE.sub("/{id}", path)
    path = _NUMERIC_RE.sub("/{id}", path)
    return path

def _safe_path_label(request, max_labels: int = 100) -> str:
    """Return the route pattern path to bound Prometheus label cardinality.

    Falls back to a normalized raw path when no route is matched, and warns
    once per unknown path pattern.
    """
    global _CARDINALITY_CAP_WARNED
    route = request.scope.get("route")
    if route is not None:
        path_attr = getattr(route, "path", None)
        if path_attr:
            return path_attr
    raw_path = request.url.path
    path = _normalize_path(raw_path)
    if path not in _PATH_CARDINALITY_WARNED:
        if len(_PATH_CARDINALITY_WARNED) < max_labels:
            _PATH_CARDINALITY_WARNED.add(path)
        elif not _CARDINALITY_CAP_WARNED:
            _CARDINALITY_CAP_WARNED = True
            logger.warning(
                "Path label cardinality cap (%d) exceeded; "
                "additional paths will still be normalized but not tracked separately. "
                "Example overflow path: %s",
                max_labels,
                path,
            )
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
