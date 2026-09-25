"""HTTP proxy API: fetch external resources with security blocks (private IP, size caps)."""

import time

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.core.log import get_logger
from app.models import ProxyRequest, ProxyResponse
from app.services.proxy_service import ProxyService

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["Proxy"])
proxy_service = ProxyService(settings)
logger = get_logger(__name__)

_PROXY_MEM_WINDOWS: dict[str, int] = {}


def _proxy_rate_limit_stub(request: Request) -> None:
    # Real per-IP limit: 10/min. Uses CacheService (shared Redis) when
    # available, else in-memory fallback. Global RateLimitMiddleware (60/min)
    # remains as outer guard.
    try:
        from app.core.cache import get_cache  # noqa: PLC0415

        cache = get_cache()
    except Exception:
        cache = None  # type: ignore[assignment]
    # Trust proxy headers only from loopback peer (same as RateLimitMiddleware).
    direct_ip = request.client.host if request.client else ""
    if direct_ip in ("127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"):
        ip = request.headers.get("X-Real-IP", "").strip() or direct_ip
    else:
        ip = direct_ip or "unknown"
    now = time.time()
    window = int(now // 60)
    key = f"proxyrl:{ip}:{window}"
    limit = 10
    if cache is not None:
        try:
            count = cache.get(key, 0) or 0
            if int(count) >= limit:
                raise HTTPException(status_code=429, detail="Proxy rate limit exceeded")
            cache.set(key, int(count) + 1, ttl=70)
            return None
        except HTTPException:
            raise
        except Exception:
            pass  # fall through to memory fallback
    bucket = _PROXY_MEM_WINDOWS.setdefault(key, 0)
    if bucket >= limit:
        raise HTTPException(status_code=429, detail="Proxy rate limit exceeded")
    _PROXY_MEM_WINDOWS[key] = bucket + 1
    # Opportunistic prune to bound memory.
    if len(_PROXY_MEM_WINDOWS) > 2000:
        cutoff = int(now // 60) - 2
        for k in list(_PROXY_MEM_WINDOWS):
            try:
                if int(k.rsplit(":", 1)[-1]) < cutoff:
                    _PROXY_MEM_WINDOWS.pop(k, None)
            except (ValueError, IndexError):
                _PROXY_MEM_WINDOWS.pop(k, None)
    return None


_STRIPPED_PROXY_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "host",
        "x-forwarded-for",
        "x-real-ip",
        "proxy-authorization",
        "te",
        "transfer-encoding",
    }
)


@router.post("/proxy-request", response_model=ProxyResponse, dependencies=[Depends(_proxy_rate_limit_stub)])
async def proxy_request(req: ProxyRequest) -> ProxyResponse:
    # Strip credentialed + routing headers so callers cannot forward ambient auth
    # or spoof upstream proxy chain.
    safe_headers = {k: v for k, v in (req.headers or {}).items() if k.lower() not in _STRIPPED_PROXY_HEADERS}
    try:
        result = await proxy_service.execute(str(req.url), req.method, safe_headers, req.body)
        return ProxyResponse(**result) if isinstance(result, dict) else result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Proxy request failed for %s", req.url)
        raise HTTPException(status_code=502, detail="Proxy request execution failed") from e

