"""Response helpers with cache-control headers."""

from typing import Any

from fastapi.responses import HTMLResponse, JSONResponse


def cached_html(content: str, status_code: int = 200, max_age: int = 86400, stale_while_revalidate: int = 604800) -> HTMLResponse:
    """Return HTML response with public cache-control."""
    return HTMLResponse(
        content=content,
        status_code=status_code,
        headers={"Cache-Control": f"public, max-age={max_age}, stale-while-revalidate={stale_while_revalidate}"},
    )


def no_cache_html(content: str, status_code: int = 200) -> HTMLResponse:
    """Return HTML response with no-cache."""
    return HTMLResponse(
        content=content,
        status_code=status_code,
        headers={"Cache-Control": "no-cache, private"},
    )


def cached_json(data: Any, max_age: int = 300, stale_while_revalidate: int = 3600) -> JSONResponse:
    """Return JSON response with public cache-control."""
    return JSONResponse(
        content=data,
        headers={"Cache-Control": f"public, max-age={max_age}, stale-while-revalidate={stale_while_revalidate}"},
    )


def no_cache_json(data: Any, status_code: int = 200) -> JSONResponse:
    """Return JSON response with no-cache."""
    return JSONResponse(
        content=data,
        status_code=status_code,
        headers={"Cache-Control": "no-cache, private"},
    )


def no_store_json(data: Any, status_code: int = 200) -> JSONResponse:
    """Return JSON response with no-store (for tracking/analytics)."""
    return JSONResponse(
        content=data,
        status_code=status_code,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
