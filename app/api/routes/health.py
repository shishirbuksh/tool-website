"""Health check and Prometheus metrics endpoints."""

import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.core.internal_guard import require_internal

__all__ = ["router"]

router = APIRouter(tags=["health"])


@router.get("/healthz", include_in_schema=False)
async def liveness():
    return JSONResponse(content={"status": "ok"})


@router.get("/readyz", include_in_schema=False)
async def readiness():
    templates_dir = settings.templates_dir
    if not os.path.exists(templates_dir):
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Templates directory not found"},
        )
    return JSONResponse(content={"status": "ok"})


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request):
    require_internal(request)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
