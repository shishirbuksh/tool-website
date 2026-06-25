import asyncio
import time

import requests
from fastapi import APIRouter

from app.core.config import Settings
from app.core.log import get_logger

router = APIRouter(prefix="/api", tags=["FearGreed"])
logger = get_logger(__name__)

settings = Settings()
_session = requests.Session()
_cache: tuple[float, dict] | None = None
_CACHE_TTL = 3600


@router.get("/fng")
async def fear_greed_index(limit: int = 31):
    global _cache
    now = time.time()
    if _cache and now - _cache[0] < _CACHE_TTL:
        return _cache[1]

    loop = asyncio.get_running_loop()

    def _fetch():
        resp = _session.get(
            f"https://api.alternative.me/fng/?limit={limit}",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    try:
        data = await loop.run_in_executor(None, _fetch)
        _cache = (time.time(), data)
        return data
    except Exception as e:
        logger.warning("fng fetch failed", exc_info=e)
        return {"name": "Fear and Greed Index", "data": [], "metadata": {"error": str(e)}}
