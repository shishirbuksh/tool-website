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
    # Rate-limit dependency stub: replace with real per-IP limiter.
    # TODO: enforce rate-limit middleware + auth guard (require_internal or API key).
    # Open proxies are abusable; at minimum rate-limit and strip credentials (see below).
    return None


@router.post("/proxy-request", response_model=ProxyResponse, dependencies=[Depends(_proxy_rate_limit_stub)])
async def proxy_request(req: ProxyRequest) -> ProxyResponse:
    # Strip credentialed headers so callers cannot forward ambient auth.
    safe_headers = {k: v for k, v in (req.headers or {}).items() if k.lower() not in ("authorization", "cookie")}
    try:
        result = await proxy_service.execute(str(req.url), req.method, safe_headers, req.body)
        return ProxyResponse(**result) if isinstance(result, dict) else result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Proxy request failed for %s", req.url)
        raise HTTPException(status_code=502, detail="Proxy request execution failed") from e

