"""Image processing API endpoints: background removal, watermark removal."""

import asyncio
import io
import re

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from PIL import Image

from app.core.config import settings
from app.core.constants import ALLOWED_IMAGE_MIMES
from app.core.log import get_logger
from app.services.image_service import ImageService

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["Image"])
image_service = ImageService(settings)
logger = get_logger(__name__)
_VALID_ALGORITHMS = {"telea", "ns"}
_BG_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_image_semaphore = None

def _get_semaphore() -> asyncio.Semaphore:
    global _image_semaphore
    if _image_semaphore is None:
        _image_semaphore = asyncio.Semaphore(3)
    return _image_semaphore

def _get_loop() -> asyncio.AbstractEventLoop:
    return asyncio.get_running_loop()


def _validate_bg_color(bg_color: str) -> str:
    if not bg_color or bg_color.strip() in ("", "transparent"):
        return bg_color
    if not _BG_COLOR_RE.match(bg_color.strip()):
        raise HTTPException(status_code=400, detail=f"Invalid bg_color '{bg_color}'. Use empty or hex like #fff / #ffffff.")
    return bg_color


def _verify_image_magic(data: bytes) -> None:
    # Magic-byte validation via PIL verify (delegates to Pillow; rejects polyglots).
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupt image data") from None
    # NOTE: dimension check enforced in service via MAX_IMAGE_PIXELS / thumbnail caps.

def _check_upload(upload: UploadFile) -> int:
    if not upload.content_type or upload.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {upload.content_type}")
    try:
        upload.file.seek(0, 2)
        size = upload.file.tell()
        upload.file.seek(0)
        return size
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not read uploaded image file") from e


@router.post("/remove-background", response_class=Response)
async def remove_background(
    image: UploadFile = File(...),  # noqa: B008
    bg_color: str = Form(""),
    smooth_edges: bool = Form(False),
) -> Response:
    if _check_upload(image) > settings.IMAGE_MAX_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit.")
    _validate_bg_color(bg_color)
    image_data = await image.read()
    _verify_image_magic(image_data)
    loop = _get_loop()
    try:
        async with _get_semaphore():
            result = await loop.run_in_executor(None, image_service.remove_background, image_data, bg_color, smooth_edges)
        return Response(content=result, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to remove background")
        raise HTTPException(status_code=500, detail="Failed to remove image background") from e


@router.post("/remove-watermark", response_class=Response)
async def remove_watermark(
    image: UploadFile = File(...),  # noqa: B008
    mask: UploadFile = File(...),  # noqa: B008
    algorithm: str = Form("telea"),
) -> Response:
    if algorithm not in _VALID_ALGORITHMS:
        raise HTTPException(status_code=400, detail=f"Invalid algorithm '{algorithm}'. Use 'telea' or 'ns'.")
    if _check_upload(image) > settings.IMAGE_MAX_SIZE or _check_upload(mask) > settings.IMAGE_MAX_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit.")

    image_data = await image.read()
    mask_data = await mask.read()
    _verify_image_magic(image_data)
    _verify_image_magic(mask_data)
    loop = _get_loop()
    try:
        async with _get_semaphore():
            result = await loop.run_in_executor(None, image_service.remove_watermark, image_data, mask_data, algorithm)
        return Response(content=result, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to remove watermark")
        raise HTTPException(status_code=500, detail="Failed to remove watermark") from e

