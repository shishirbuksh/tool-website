"""NFT generation API: text-to-image via local/remote AI providers."""

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.log import get_logger
from app.models import NFTRequest, NFTResponse
from app.services.fractal_service import FractalService

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["NFT"])
fractal_service = FractalService(settings)
logger = get_logger(__name__)


@router.post("/generate-nft", response_model=NFTResponse)
async def generate_nft(req: NFTRequest) -> NFTResponse:
    raw_key = req.api_key.get_secret_value() if req.api_key is not None else None
    # SecretStr unwrapped here; blank keys already rejected by model validation.
    if not raw_key and req.provider != "local":
        raise HTTPException(status_code=401, detail="API Key required")
    # Defense in depth: prompt length check (model also enforces 1-2000).
    if not req.prompt or not 1 <= len(req.prompt) <= 2000:
        raise HTTPException(status_code=422, detail="Prompt must be 1-2000 characters")
    try:
        result = await fractal_service.generate_nft(
            prompt=req.prompt,
            style=req.style,
            provider=req.provider,
            api_key=raw_key,
        )
        return NFTResponse(**result) if isinstance(result, dict) else result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("NFT generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate NFT") from e

