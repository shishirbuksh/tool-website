"""PDF conversion API endpoints: image-to-PDF, text-to-PDF."""

import io
import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.constants import ALLOWED_IMAGE_MIMES
from app.core.log import get_logger
from app.services.pdf_service import PDFService

ALLOWED_TEXT_MIMES = {"text/plain"}

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["PDF"])
pdf_service = PDFService(settings)
logger = get_logger(__name__)


def _pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )


@router.post("/convert-to-pdf")
async def convert_to_pdf(file: UploadFile = File(...)):  # noqa: B008
    filename = file.filename.lower()
    base_name = os.path.splitext(file.filename)[0]
    max_size = settings.PDF_MAX_SIZE

    if file.content_type not in ALLOWED_IMAGE_MIMES and file.content_type not in ALLOWED_TEXT_MIMES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size > max_size:
        raise HTTPException(status_code=413, detail="File size exceeds 5MB limit.")

    if file.content_type in ALLOWED_IMAGE_MIMES:
        image_data = await file.read()
        pdf_bytes = pdf_service.convert_image_to_pdf(image_data, filename)
        return _pdf_response(pdf_bytes, base_name)

    if file.content_type in ALLOWED_TEXT_MIMES:
        text_data = await file.read()
        pdf_bytes = pdf_service.convert_text_to_pdf(text_data)
        return _pdf_response(pdf_bytes, base_name)

    raise HTTPException(
        status_code=400,
        detail="Unsupported file format. Only Images and TXT files are supported.",
    )
