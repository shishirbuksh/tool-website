from fastapi import APIRouter

from app.core.config import settings
from app.core.log import get_logger
from app.models import NFTRequest
from app.services.fractal_service import FractalService

router = APIRouter(prefix="/api", tags=["NFT"])
fractal_service = FractalService(settings)
logger = get_logger(__name__)


@router.post("/generate-nft")
async def generate_nft(req: NFTRequest):
    return await fractal_service.generate_nft(
        prompt=req.prompt,
        style=req.style,
        provider=req.provider,
        api_key=req.api_key,
    )
