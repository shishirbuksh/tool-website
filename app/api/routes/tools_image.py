from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.core.config import settings
from app.core.log import get_logger
from app.services.image_service import ImageService

router = APIRouter(prefix="/api", tags=["Image"])
image_service = ImageService(settings)
logger = get_logger(__name__)

MAX_IMAGE_SIZE = 10 * 1024 * 1024


def _check_size(upload: UploadFile) -> int:
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(0)
    return size


@router.post("/remove-background")
async def remove_background(
    image: UploadFile = File(...),
    bg_color: str = Form(""),
    smooth_edges: bool = Form(False),
):
    if _check_size(image) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit.")
    image_data = await image.read()
    result = image_service.remove_background(image_data, bg_color, smooth_edges)
    return Response(content=result, media_type="image/png")


@router.post("/remove-watermark")
async def remove_watermark(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    algorithm: str = Form("telea"),
):
    if _check_size(image) > MAX_IMAGE_SIZE or _check_size(mask) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit.")

    image_data = await image.read()
    mask_data = await mask.read()
    result = image_service.remove_watermark(image_data, mask_data, algorithm)
    return Response(content=result, media_type="image/png")
