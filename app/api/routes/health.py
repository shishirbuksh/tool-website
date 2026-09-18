"""Health check and Prometheus metrics endpoints."""

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.core.internal_guard import require_internal
from app.core.log import get_logger

__all__ = ["router"]

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/healthz", include_in_schema=False)
async def liveness() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})


@router.get("/readyz", include_in_schema=False)
async def readiness() -> JSONResponse:
    try:
        templates_dir = settings.templates_dir
        if not os.path.exists(templates_dir):
            return JSONResponse(
                status_code=503,
                content={"status": "error", "detail": "Templates directory not found"},
            )
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.exception("Readiness check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": f"Readiness check failed: {e}"},
        )


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    require_internal(request)
    try:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.exception("Metrics generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate metrics") from e

