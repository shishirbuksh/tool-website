"""Shared internal-only request guard used by metrics and analytics endpoints."""

from fastapi import HTTPException, Request

_INTERNAL_IPS = {"127.0.0.1", "::1", "localhost"}


def require_internal(request: Request) -> None:
    """Raise HTTP 403 if the request does not come from localhost / internal network.

    Security: Only trust X-Real-IP when the direct connection comes from a known
    proxy (e.g. Caddy on localhost). If X-Real-IP is present but the ASGI client
    host is NOT a trusted proxy, reject the forged header.
    """
    real_ip = request.headers.get("X-Real-IP", "")
    client_host = request.client.host if request.client else ""

    if real_ip and client_host and client_host not in _INTERNAL_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")

    client_ip = real_ip or client_host
    if client_ip not in _INTERNAL_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")
