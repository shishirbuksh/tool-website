from fastapi import APIRouter

from app.core.config import settings
from app.core.log import get_logger
from app.services.crypto_service import CryptoService
from app.services.job_service import get_job_service

router = APIRouter(prefix="/api", tags=["Crypto"])
crypto_service = CryptoService(settings)
job_service = get_job_service()
logger = get_logger(__name__)


@router.get("/predict-crypto")
async def predict_crypto(symbol: str = "BTC-USD"):
    return await crypto_service.predict(symbol)


@router.get("/predict-crypto-async")
async def predict_crypto_async(symbol: str = "BTC-USD"):
    return job_service.submit(
        name=f"predict:{symbol}",
        coro_factory=lambda: crypto_service.predict(symbol),
    )


@router.get("/analyze-crypto-trend")
async def analyze_crypto_trend(symbol: str = "BTC-USD"):
    return await crypto_service.analyze_trend(symbol)


@router.get("/analyze-crypto-trend-async")
async def analyze_crypto_trend_async(symbol: str = "BTC-USD"):
    return job_service.submit(
        name=f"trend:{symbol}",
        coro_factory=lambda: crypto_service.analyze_trend(symbol),
    )
