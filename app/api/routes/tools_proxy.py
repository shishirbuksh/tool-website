from fastapi import APIRouter

from app.core.config import settings
from app.core.log import get_logger
from app.models import ProxyRequest
from app.services.proxy_service import ProxyService

router = APIRouter(prefix="/api", tags=["Proxy"])
proxy_service = ProxyService(settings)
logger = get_logger(__name__)


@router.post("/proxy-request")
async def proxy_request(req: ProxyRequest):
    return await proxy_service.execute(req.url, req.method, req.headers, req.body)
