"""Shared internal-only request guard used by metrics and analytics endpoints."""

from fastapi import HTTPException, Request

_INTERNAL_IPS = {"127.0.0.1", "::1", "localhost"}


def require_internal(request: Request) -> None:
    """Raise HTTP 403 if the request does not come from localhost / internal network.

    Caddy sets X-Real-IP to the actual client IP. Falls back to the ASGI
    client address when running without a reverse proxy (local dev).
    """
    real_ip = request.headers.get("X-Real-IP", "")
    client_ip = real_ip or (request.client.host if request.client else "")
    if client_ip not in _INTERNAL_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")
