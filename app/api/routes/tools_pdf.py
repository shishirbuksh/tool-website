"""PDF conversion API endpoints: image-to-PDF, text-to-PDF."""

import asyncio
import io
import os
import re
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.constants import ALLOWED_IMAGE_MIMES
from app.core.exceptions import ValidationException
from app.core.log import get_logger
from app.services.pdf_service import PDFService

ALLOWED_TEXT_MIMES = {"text/plain"}

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["PDF"])
pdf_service = PDFService(settings)
logger = get_logger(__name__)

_FILENAME_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9-_]+")
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
_TEXT_EXTS = {".txt"}


def _sanitize_filename(filename: str) -> str:
    # Strip directories, replace unsafe chars, truncate to 100 chars.
    base = os.path.basename(filename)
    base = os.path.splitext(base)[0]
    safe = _FILENAME_SANITIZE_RE.sub("_", base).strip("_")
    if not safe:
        safe = "document"
    return safe[:100]


def _pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    safe = _sanitize_filename(filename)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}.pdf"; filename*=UTF-8\'\'{quote(safe + ".pdf")}'},
    )


@router.post("/convert-to-pdf", response_class=StreamingResponse)
async def convert_to_pdf(file: UploadFile = File(...)) -> StreamingResponse:  # noqa: B008
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    filename = file.filename.lower()
    base_name = os.path.splitext(file.filename)[0]
    ext = os.path.splitext(filename)[1]
    max_size = settings.PDF_MAX_SIZE

    if not file.content_type or (file.content_type not in ALLOWED_IMAGE_MIMES and file.content_type not in ALLOWED_TEXT_MIMES):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    # Check extension vs content_type mismatch.
    if file.content_type in ALLOWED_IMAGE_MIMES and ext not in _IMAGE_EXTS:
        raise HTTPException(status_code=400, detail=f"Extension '{ext}' does not match content type '{file.content_type}'")
    if file.content_type in ALLOWED_TEXT_MIMES and ext not in _TEXT_EXTS:
        raise HTTPException(status_code=400, detail=f"Extension '{ext}' does not match content type '{file.content_type}'")

    try:
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not read uploaded file") from e

    if size > max_size:
        raise HTTPException(status_code=413, detail="File size exceeds 5MB limit.")

    if file.content_type in ALLOWED_IMAGE_MIMES:
        image_data = await file.read()
        loop = asyncio.get_running_loop()
        try:
            pdf_bytes = await loop.run_in_executor(None, pdf_service.convert_image_to_pdf, image_data, filename)
            return _pdf_response(pdf_bytes, base_name)
        except (HTTPException, ValidationException):
            raise
        except Exception as e:
            logger.exception("Failed to convert image to PDF for %s", filename)
            raise HTTPException(status_code=400, detail="Invalid or corrupt image file") from e

    if file.content_type in ALLOWED_TEXT_MIMES:
        text_data = await file.read()
        loop = asyncio.get_running_loop()
        try:
            pdf_bytes = await loop.run_in_executor(None, pdf_service.convert_text_to_pdf, text_data)
            return _pdf_response(pdf_bytes, base_name)
        except (HTTPException, ValidationException):
            raise
        except Exception as e:
            logger.exception("Failed to convert text to PDF")
            raise HTTPException(status_code=400, detail="Failed to convert text to PDF") from e

    raise HTTPException(
        status_code=400,
        detail="Unsupported file format. Only Images and TXT files are supported.",
    )

