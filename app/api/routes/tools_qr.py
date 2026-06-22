from fastapi import APIRouter, Form, Response

from app.core.config import settings
from app.services.qr_service import QRService

router = APIRouter(prefix="/api", tags=["QR"])
qr_service = QRService(settings)


@router.post("/generate-qr")
async def generate_qr(
    data: str = Form(...),
    fg_color: str = Form("black"),
    bg_color: str = Form("white"),
    error_correction: str = Form("L"),
):
    png_bytes = qr_service.generate(data, fg_color, bg_color, error_correction)
    return Response(content=png_bytes, media_type="image/png")
