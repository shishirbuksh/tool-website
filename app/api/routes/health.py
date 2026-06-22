import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/healthz", include_in_schema=False)
async def liveness():
    return JSONResponse(content={"status": "ok"})


@router.get("/readyz", include_in_schema=False)
async def readiness():
    templates_dir = settings.TEMPLATES_DIR
    if not os.path.exists(templates_dir):
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Templates directory not found"},
        )
    return JSONResponse(content={"status": "ok"})


@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
