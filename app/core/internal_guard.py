"""Shared internal-only request guard used by metrics and analytics endpoints."""

from fastapi import HTTPException, Request

# Localhost allowlist: loopback IPv4/IPv6 + Caddy-on-localhost proxy mapping.
# "localhost" hostname is included for test clients that set client.host literally;
# DNS rebinding is not a concern here because we also require the direct ASGI peer
# to be loopback and cross-check X-Real-IP vs rightmost X-Forwarded-For.
_INTERNAL_IPS = {"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"}


def require_internal(request: Request) -> None:
    """Raise HTTP 403 if the request does not come from localhost / internal network.

    Security: Only trust X-Real-IP / X-Forwarded-For when the direct connection
    comes from a known proxy (e.g. Caddy on localhost). If proxy headers are
    present but the ASGI client host is NOT a trusted proxy, reject the forged
    headers. When both headers exist they must agree (rightmost XFF == X-Real-IP).
    """
    real_ip = request.headers.get("X-Real-IP", "").strip()
    xff = request.headers.get("X-Forwarded-For", "")
    xff_last = xff.split(",")[-1].strip() if xff else ""
    client_host = request.client.host if request.client else ""

    if not client_host or client_host not in _INTERNAL_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")

    if real_ip and xff_last and real_ip != xff_last:
        raise HTTPException(status_code=403, detail="Forbidden")

    client_ip = real_ip or xff_last or client_host
    if client_ip not in _INTERNAL_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")
