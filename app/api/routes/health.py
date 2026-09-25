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
        if not os.path.exists(settings.templates_dir):
            return JSONResponse(
                status_code=503,
                content={"status": "error", "detail": "Templates directory not found"},
            )
        if not os.path.exists(settings.static_dir):
            return JSONResponse(
                status_code=503,
                content={"status": "error", "detail": "Static directory not found"},
            )
        var_data = os.path.join(settings.base_dir, "var", "data")
        try:
            os.makedirs(var_data, exist_ok=True)
            probe = os.path.join(var_data, f".readyz_probe_{os.getpid()}")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "detail": "var/data not writable"},
            )
        # DB file must exist/writable after lifespan pool init.
        try:
            db_path = os.path.join(var_data, "analytics.db")
            if os.path.exists(db_path) and not os.access(db_path, os.W_OK):
                return JSONResponse(
                    status_code=503,
                    content={"status": "error", "detail": "analytics DB not writable"},
                )
        except Exception:
            pass
        if not (settings.REDIS_URL or "").strip():
            return JSONResponse(content={"status": "ok", "checks": {"redis": "in-memory fallback"}})
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.exception("Readiness check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": f"Readiness check failed: {e}"},
        )


@router.get("/versionz", include_in_schema=False)
async def version() -> JSONResponse:
    return JSONResponse(
        content={
            "status": "ok",
            "version": os.getenv("APP_VERSION", "dev"),
        }
    )


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    require_internal(request)
    try:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.exception("Metrics generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate metrics") from e

