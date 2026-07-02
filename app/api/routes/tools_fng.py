"""Fear & Greed Index proxy endpoint: fetches from alternative.me API."""

import asyncio
import time

import requests
from fastapi import APIRouter, HTTPException

from app.core.log import get_logger

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["FearGreed"])
logger = get_logger(__name__)
_CACHE_TTL = 3600


def _get_cached_fng(limit: int) -> dict | None:
    cache: dict = getattr(_get_cached_fng, "_cache", None)
    if cache and limit in cache and time.time() - cache[limit][0] < _CACHE_TTL:
        return cache[limit][1]
    return None


def _set_cached_fng(limit: int, data: dict):
    cache: dict = getattr(_get_cached_fng, "_cache", None)
    if cache is None:
        _get_cached_fng._cache = {}
        cache = _get_cached_fng._cache
    cache[limit] = (time.time(), data)


@router.get("/fng")
async def fear_greed_index(limit: int = 31):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    cached = _get_cached_fng(limit)
    if cached is not None:
        return cached

    loop = asyncio.get_running_loop()

    def _fetch():
        resp = requests.get(
            f"https://api.alternative.me/fng/?limit={limit}",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    try:
        data = await loop.run_in_executor(None, _fetch)
        _set_cached_fng(limit, data)
        return data
    except Exception as e:
        logger.warning("fng fetch failed", exc_info=e)
        return {"name": "Fear and Greed Index", "data": [], "metadata": {"error": str(e)}}
