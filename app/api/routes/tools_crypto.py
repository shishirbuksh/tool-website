"""Crypto prediction and trend analysis API (async job-based)."""

import re

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.log import get_logger
from app.services.crypto_service import CryptoService
from app.services.job_service import get_job_service

__all__ = ["router"]

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,10}-[A-Z0-9]{2,10}$")

router = APIRouter(prefix="/api", tags=["Crypto"])
crypto_service = CryptoService(settings)
job_service = get_job_service()
logger = get_logger(__name__)


def _validate_symbol(symbol: str):
    if not _SYMBOL_RE.match(symbol):
        raise HTTPException(status_code=400, detail=f"Invalid symbol format: {symbol}")


@router.get("/predict-crypto")
async def predict_crypto(symbol: str = "BTC-USD"):
    _validate_symbol(symbol)
    return await crypto_service.predict(symbol)


@router.get("/predict-crypto-async")
async def predict_crypto_async(symbol: str = "BTC-USD"):
    _validate_symbol(symbol)
    return job_service.submit(
        name=f"predict:{symbol}",
        coro_factory=lambda: crypto_service.predict(symbol),
    )


@router.get("/analyze-crypto-trend")
async def analyze_crypto_trend(symbol: str = "BTC-USD"):
    _validate_symbol(symbol)
    return await crypto_service.analyze_trend(symbol)


@router.get("/analyze-crypto-trend-async")
async def analyze_crypto_trend_async(symbol: str = "BTC-USD"):
    _validate_symbol(symbol)
    return job_service.submit(
        name=f"trend:{symbol}",
        coro_factory=lambda: crypto_service.analyze_trend(symbol),
    )
