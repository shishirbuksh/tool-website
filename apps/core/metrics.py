"""Metrics middleware and Prometheus counters."""

from __future__ import annotations

import re
import time
from prometheus_client import Counter, Gauge, Histogram
from apps.core.log import get_logger

logger = get_logger(__name__)

_PATH_CARDINALITY_WARNED: set[str] = set()
_CARDINALITY_CAP_WARNED = False

_UUID_RE = re.compile(r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)")
_NUMERIC_RE = re.compile(r"/\d+(?=/|$)")
_TOOL_SLUG_RE = re.compile(r"^/tool/[^/]+")
_PAGE_RE = re.compile(r"^/(about|contact|privacy|terms|disclaimer)/?$")


def reset_cardinality() -> None:
    global _CARDINALITY_CAP_WARNED
    _PATH_CARDINALITY_WARNED.clear()
    _CARDINALITY_CAP_WARNED = False


def _normalize_path(path: str) -> str:
    if path.startswith("/static/"):
        return "/static/*"
    if _PAGE_RE.match(path):
        return "/{page}"
    if _TOOL_SLUG_RE.match(path):
        path = _TOOL_SLUG_RE.sub("/tool/{slug}", path, count=1)
    path = _UUID_RE.sub("/{id}", path)
    path = _NUMERIC_RE.sub("/{id}", path)
    return path


def _safe_path_label(request, max_labels: int = 100) -> str:
    global _CARDINALITY_CAP_WARNED
    raw_path = getattr(request, "path", "/")
    path = _normalize_path(raw_path)
    if path not in _PATH_CARDINALITY_WARNED:
        if len(_PATH_CARDINALITY_WARNED) < max_labels:
            _PATH_CARDINALITY_WARNED.add(path)
        elif not _CARDINALITY_CAP_WARNED:
            _CARDINALITY_CAP_WARNED = True
            logger.warning("Path label cardinality cap exceeded: %s", path)
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


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        active_requests.inc()
        start = time.monotonic()
        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            elapsed = time.monotonic() - start
            status = getattr(response, "status_code", 500)
            active_requests.dec()
            path = _safe_path_label(request)
            request_count.labels(method=request.method, path=path, status=status).inc()
            request_latency.labels(method=request.method, path=path).observe(elapsed)
