"""HTTP proxy API: fetch external resources with security blocks (private IP, size caps)."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.log import get_logger
from app.models import ProxyRequest, ProxyResponse
from app.services.proxy_service import ProxyService

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["Proxy"])
proxy_service = ProxyService(settings)
logger = get_logger(__name__)


async def _proxy_rate_limit_stub() -> None:
    # Global RateLimitMiddleware already enforces 60/min on POST /api/proxy-request.
    # This dependency exists to keep an explicit hook for future per-URL quotas/API keys.
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

