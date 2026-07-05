"""Response helpers with cache-control headers."""

from fastapi.responses import HTMLResponse, JSONResponse


def cached_html(content: str, status_code: int = 200, max_age: int = 86400, stale_while_revalidate: int = 604800):
    """Return HTML response with public cache-control."""
    return HTMLResponse(
        content=content,
        status_code=status_code,
        headers={"Cache-Control": f"public, max-age={max_age}, stale-while-revalidate={stale_while_revalidate}"},
    )


def no_cache_html(content: str, status_code: int = 200):
    """Return HTML response with no-cache."""
    return HTMLResponse(
        content=content,
        status_code=status_code,
        headers={"Cache-Control": "no-cache, private"},
    )


def cached_json(data, max_age: int = 300, stale_while_revalidate: int = 3600):
    """Return JSON response with public cache-control."""
    return JSONResponse(
        content=data,
        headers={"Cache-Control": f"public, max-age={max_age}, stale-while-revalidate={stale_while_revalidate}"},
    )


def no_cache_json(data, status_code: int = 200):
    """Return JSON response with no-cache."""
    return JSONResponse(
        content=data,
        status_code=status_code,
        headers={"Cache-Control": "no-cache, private"},
    )


def no_store_json(data, status_code: int = 200):
    """Return JSON response with no-store (for tracking/analytics)."""
    return JSONResponse(
        content=data,
        status_code=status_code,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
