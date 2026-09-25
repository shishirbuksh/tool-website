"""Crypto prediction and trend analysis API (async job-based)."""

import re
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.exceptions import ServiceError
from app.core.log import get_logger
from app.models.job import JobResponse
from app.services.crypto_service import CryptoService
from app.services.job_service import get_job_service

__all__ = ["router"]

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,10}-[A-Z0-9]{2,10}$")

router = APIRouter(prefix="/api", tags=["Crypto"])
crypto_service = CryptoService(settings)
job_service = get_job_service()
logger = get_logger(__name__)

# NOTE: async job endpoints use GET for backwards compat (deprecated).
# Prefer POST for new clients to avoid cache/CDN issues and enable rate-limiting.
# TODO: ensure per-IP rate-limit middleware covers these expensive endpoints.


def _validate_symbol(symbol: Any) -> str:
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        raise HTTPException(status_code=400, detail=f"Invalid symbol format: {symbol}")
    normalized = symbol.upper().strip()
    if not _SYMBOL_RE.match(normalized):
        raise HTTPException(status_code=400, detail=f"Invalid symbol format: {symbol}")
    return normalized


def _service_error_to_502(e: ServiceError) -> HTTPException:
    # Upstream/service failures (exchanges, ML) are 502, not 400.
    return HTTPException(status_code=502, detail=str(e.detail) if hasattr(e, "detail") else "Service error")


def _submit(name: str, coro_factory: Callable[[], Coroutine[Any, Any, Any]]) -> JobResponse:
    try:
        return job_service.submit(name=name, coro_factory=coro_factory)
    except Exception as e:
        logger.exception("Failed to schedule job %s", name)
        raise HTTPException(status_code=503, detail="Failed to schedule job") from e


@router.get("/predict-crypto")
async def predict_crypto(symbol: str = "BTC-USD") -> dict[str, Any]:
    symbol = _validate_symbol(symbol)
    try:
        return await crypto_service.predict(symbol)
    except ServiceError as e:
        raise _service_error_to_502(e) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in predict_crypto for %s", symbol)
        raise HTTPException(status_code=500, detail="Prediction failed") from e


@router.get("/predict-crypto-async", response_model=JobResponse, deprecated=True)
async def predict_crypto_async(symbol: str = "BTC-USD") -> JobResponse:
    symbol = _validate_symbol(symbol)
    return _submit(
        name=f"predict:{symbol}",
        coro_factory=lambda s=symbol: crypto_service.predict(s),
    )


@router.post("/predict-crypto-async", response_model=JobResponse, include_in_schema=False)
async def predict_crypto_async_post(payload: dict[str, Any] | None = None) -> JobResponse:
    symbol = _validate_symbol((payload or {}).get("symbol", "BTC-USD"))
    return _submit(
        name=f"predict:{symbol}",
        coro_factory=lambda s=symbol: crypto_service.predict(s),
    )


@router.get("/analyze-crypto-trend")
async def analyze_crypto_trend(symbol: str = "BTC-USD") -> dict[str, Any]:
    symbol = _validate_symbol(symbol)
    try:
        return await crypto_service.analyze_trend(symbol)
    except ServiceError as e:
        raise _service_error_to_502(e) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in analyze_crypto_trend for %s", symbol)
        raise HTTPException(status_code=500, detail="Trend analysis failed") from e


@router.get("/analyze-crypto-trend-async", response_model=JobResponse, deprecated=True)
async def analyze_crypto_trend_async(symbol: str = "BTC-USD") -> JobResponse:
    symbol = _validate_symbol(symbol)
    return _submit(
        name=f"trend:{symbol}",
        coro_factory=lambda s=symbol: crypto_service.analyze_trend(s),
    )


@router.post("/analyze-crypto-trend-async", response_model=JobResponse, include_in_schema=False)
async def analyze_crypto_trend_async_post(payload: dict[str, Any] | None = None) -> JobResponse:
    symbol = _validate_symbol((payload or {}).get("symbol", "BTC-USD"))
    return _submit(
        name=f"trend:{symbol}",
        coro_factory=lambda s=symbol: crypto_service.analyze_trend(s),
    )

