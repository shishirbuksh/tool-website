"""Image processing API endpoints: background removal, watermark removal."""

import asyncio

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.core.config import settings
from app.core.constants import ALLOWED_IMAGE_MIMES
from app.services.image_service import ImageService

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["Image"])
image_service = ImageService(settings)
_VALID_ALGORITHMS = {"telea", "ns"}
_image_semaphore = None

def _get_semaphore():
    global _image_semaphore
    if _image_semaphore is None:
        _image_semaphore = asyncio.Semaphore(3)
    return _image_semaphore

def _get_loop():
    return asyncio.get_event_loop()

def _check_upload(upload: UploadFile) -> int:
    if upload.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {upload.content_type}")
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(0)
    return size


@router.post("/remove-background")
async def remove_background(
    image: UploadFile = File(...),  # noqa: B008
    bg_color: str = Form(""),
    smooth_edges: bool = Form(False),
):
    if _check_upload(image) > settings.IMAGE_MAX_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit.")
    image_data = await image.read()
    loop = _get_loop()
    async with _get_semaphore():
        result = await loop.run_in_executor(None, image_service.remove_background, image_data, bg_color, smooth_edges)
    return Response(content=result, media_type="image/png")


@router.post("/remove-watermark")
async def remove_watermark(
    image: UploadFile = File(...),  # noqa: B008
    mask: UploadFile = File(...),  # noqa: B008
    algorithm: str = Form("telea"),
):
    if algorithm not in _VALID_ALGORITHMS:
        raise HTTPException(status_code=400, detail=f"Invalid algorithm '{algorithm}'. Use 'telea' or 'ns'.")
    if _check_upload(image) > settings.IMAGE_MAX_SIZE or _check_upload(mask) > settings.IMAGE_MAX_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit.")

    image_data = await image.read()
    mask_data = await mask.read()
    loop = _get_loop()
    async with _get_semaphore():
        result = await loop.run_in_executor(None, image_service.remove_watermark, image_data, mask_data, algorithm)
    return Response(content=result, media_type="image/png")
