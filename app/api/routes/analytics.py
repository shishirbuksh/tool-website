"""Analytics tracking API: record page views and retrieve top pages."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.internal_guard import require_internal
from app.services.analytics_service import async_get_counts, async_track

__all__ = ["router"]

router = APIRouter(tags=["analytics"])


class TrackPayload(BaseModel):
    name: str = Field(..., max_length=200)
    category: str = Field("page_view", max_length=50)


@router.post("/api/track")
async def api_track(payload: TrackPayload):
    await async_track(payload.name, payload.category)
    return {"ok": True}


@router.get("/api/analytics/top")
async def api_analytics_top(request: Request, limit: int = 50):
    require_internal(request)
    return await async_get_counts(limit=limit)
