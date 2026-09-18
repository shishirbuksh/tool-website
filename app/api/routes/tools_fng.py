"""Fear & Greed Index proxy endpoint: fetches from alternative.me API."""

import asyncio
import copy
import time

from typing import Any

import requests
from fastapi import APIRouter, HTTPException

from app.core.log import get_logger

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["FearGreed"])
logger = get_logger(__name__)
_CACHE_TTL = 3600

# Singleflight locks per limit to avoid cache stampede.
_FNG_LOCKS: dict[int, asyncio.Lock] = {}


def _get_fng_lock(limit: int) -> asyncio.Lock:
    lock = _FNG_LOCKS.get(limit)
    if lock is None:
        lock = asyncio.Lock()
        _FNG_LOCKS[limit] = lock
    return lock


def _get_cached_fng(limit: int) -> dict[str, Any] | None:
    cache: dict = getattr(_get_cached_fng, "_cache", None)
    if cache and limit in cache and time.time() - cache[limit][0] < _CACHE_TTL:
        return cache[limit][1]
    return None


def _set_cached_fng(limit: int, data: dict[str, Any]) -> None:
    try:
        cache: dict = getattr(_get_cached_fng, "_cache", None)
        if cache is None:
            _get_cached_fng._cache = {}
            cache = _get_cached_fng._cache
        # Copy before caching to avoid caller mutation of cached object.
        cache[limit] = (time.time(), copy.deepcopy(data))
    except Exception as e:
        logger.warning("Failed to cache FNG data: %s", e)


@router.get("/fng", response_model=dict[str, Any])
async def fear_greed_index(limit: int = 31) -> dict[str, Any]:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    lock = _get_fng_lock(limit)
    async with lock:
        cached = _get_cached_fng(limit)
        if cached is not None:
            # Return a copy so callers cannot mutate the cache.
            return copy.deepcopy(cached)

        loop = asyncio.get_running_loop()

        def _fetch() -> dict[str, Any]:
            resp = requests.get(
                f"https://api.alternative.me/fng/?limit={limit}",
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()

        try:
            data = await loop.run_in_executor(None, _fetch)
            _set_cached_fng(limit, data)
            return copy.deepcopy(data)
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("fng fetch failed", exc_info=e)
            raise HTTPException(status_code=502, detail="Upstream Fear & Greed service unavailable") from e

