"""PDF conversion service: image-to-PDF and text-to-PDF with PIL-based image handling."""

import io
import os

from fpdf import FPDF
from PIL import Image

from app.core.config import Settings

# Decompression bomb protection
Image.MAX_IMAGE_PIXELS = 178_000_000


def _find_unicode_font() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        os.path.expanduser("~/.fonts/DejaVuSans.ttf"),
        "C:\\Windows\\Fonts\\DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


class PDFService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._unicode_font = _find_unicode_font()

    def convert_image_to_pdf(self, image_data: bytes, filename: str) -> bytes:
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        pdf_buf = io.BytesIO()
        image.save(pdf_buf, format="PDF", resolution=100.0)
        pdf_buf.seek(0)
        return pdf_buf.read()

    def convert_text_to_pdf(self, text_data: bytes) -> bytes:
        pdf = FPDF()
        pdf.add_page()
        if self._unicode_font:
            pdf.add_font("Unicode", "", self._unicode_font)
            pdf.set_font("Unicode", size=12)
        else:
            pdf.set_font("Helvetica", size=12)

        try:
            text = text_data.decode("utf-8")
        except UnicodeDecodeError:
            text = text_data.decode("latin-1")

        if not self._unicode_font:
            text = text.encode("latin-1", "replace").decode("latin-1")
        text = text.replace("\r", "")
        pdf.multi_cell(w=0, h=10, text=text)

        pdf_buf = io.BytesIO(pdf.output())
        pdf_buf.seek(0)
        return pdf_buf.read()
