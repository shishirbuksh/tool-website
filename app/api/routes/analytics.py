from fastapi import APIRouter
from pydantic import BaseModel

from app.services.analytics_service import get_counts, track

router = APIRouter(tags=["analytics"])


class TrackPayload(BaseModel):
    name: str
    category: str = "page_view"


@router.post("/api/track")
async def api_track(payload: TrackPayload):
    track(payload.name, payload.category)
    return {"ok": True}


@router.get("/api/analytics/top")
async def api_analytics_top(limit: int = 50):
    return get_counts(limit=limit)
