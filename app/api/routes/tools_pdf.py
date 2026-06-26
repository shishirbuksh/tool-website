import io
import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.log import get_logger
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/api", tags=["PDF"])
pdf_service = PDFService(settings)
logger = get_logger(__name__)


@router.post("/convert-to-pdf")
async def convert_to_pdf(file: UploadFile = File(...)):  # noqa: B008
    filename = file.filename.lower()
    base_name = os.path.splitext(file.filename)[0]
    max_size = 5 * 1024 * 1024

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size > max_size:
        raise HTTPException(status_code=413, detail="File size exceeds 5MB limit.")

    if filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        image_data = await file.read()
        pdf_bytes = pdf_service.convert_image_to_pdf(image_data, filename)
        pdf_buf = io.BytesIO(pdf_bytes)
        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.pdf"'},
        )

    elif filename.endswith(".txt"):
        text_data = await file.read()
        pdf_bytes = pdf_service.convert_text_to_pdf(text_data)
        pdf_buf = io.BytesIO(pdf_bytes)
        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.pdf"'},
        )

    raise HTTPException(
        status_code=400,
        detail="Unsupported file format. Only Images and TXT files are supported.",
    )
