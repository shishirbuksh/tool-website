"""Analytics tracking API: record page views and retrieve top pages."""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.internal_guard import require_internal
from app.core.log import get_logger
from app.services.analytics_service import async_get_counts, async_track

__all__ = ["router"]

router = APIRouter(tags=["analytics"])
logger = get_logger(__name__)


class TrackPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, pattern=r"^[^\r\n]*$")
    category: str = Field("page_view", min_length=1, max_length=50, pattern=r"^[^\r\n]*$")


class TrackResponse(BaseModel):
    ok: bool = Field(default=True, description="Tracking acknowledgment")
    dropped: bool = Field(default=False, description="True when event was dropped (pool/full) but accepted")


@router.post("/api/track", response_model=TrackResponse, status_code=200)
async def api_track(payload: TrackPayload) -> TrackResponse:
    # TODO: add rate-limit middleware (e.g. per-IP token bucket) if not present globally.
    # ROUND-2: fire-and-forget semantics — never 500 on tracking failure.
    # Return 200 with dropped flag so clients don't retry storms (kept 200 for backward compat with tests/beacon).
    try:
        ok = await async_track(payload.name, payload.category)
        if not ok:
            logger.warning("Analytics event dropped for %s", payload.name)
            return TrackResponse(ok=True, dropped=True)
        return TrackResponse(ok=True, dropped=False)
    except Exception as e:
        logger.exception("Failed to record analytics event for %s", payload.name)
        # Still 200 + dropped (don't fail the page view on analytics outage).
        return TrackResponse(ok=True, dropped=True)


@router.get("/api/analytics/top", response_model=dict[str, int])
async def api_analytics_top(
    request: Request,
    limit: int = Query(default=50, ge=1, le=1000),
) -> dict[str, int]:
    require_internal(request)
    try:
        return await async_get_counts(limit=limit)
    except Exception as e:
        logger.exception("Failed to retrieve top analytics counts")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics data") from e

