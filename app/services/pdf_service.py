"""PDF conversion service: image-to-PDF and text-to-PDF with PIL-based image handling."""

import io
import os
import re

from fpdf import FPDF
from PIL import Image

from app.core.config import Settings
from app.core.constants import MAX_IMAGE_PIXELS
from app.core.exceptions import ValidationException

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

MAX_TEXT_CHARS = 200_000


def _sanitize_filename(filename: str, default: str = "document") -> str:
    """Basename + strip CR/LF + limit length. Full path sanitization happens upstream."""
    if not filename:
        return default
    name = os.path.basename(str(filename)).replace("\r", "").replace("\n", "").strip()
    # Drop characters unsafe for PDF metadata / headers.
    name = re.sub(r"[^\w\-. ]+", "_", name)
    name = name[:100] or default
    return name


def _fpdf_output_bytes(pdf: FPDF) -> bytes:
    """Handle fpdf vs fpdf2 output types (str vs bytes/bytearray)."""
    out = pdf.output()
    if isinstance(out, str):
        return out.encode("latin-1")
    # fpdf2 returns bytearray; bytes() normalizes both.
    return bytes(out)


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
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._unicode_font = _find_unicode_font()

    def convert_image_to_pdf(self, image_data: bytes, filename: str) -> bytes:
        # Filename used only for metadata/header; sanitized upstream + here.
        filename = _sanitize_filename(filename)
        if not image_data:
            raise ValidationException("Image data must not be empty")
        if len(image_data) > getattr(self.settings, "IMAGE_MAX_SIZE", 50 * 1024 * 1024):
            raise ValidationException("Image file size exceeds limit (50MB)")
        try:
            with Image.open(io.BytesIO(image_data)) as image:
                if (image.width * image.height) > MAX_IMAGE_PIXELS:
                    raise ValidationException(f"Image exceeds maximum pixel limit ({MAX_IMAGE_PIXELS})")
                rgb_image = image.convert("RGB")
                pdf_buf = io.BytesIO()
                rgb_image.save(pdf_buf, format="PDF", resolution=100.0)
                pdf_buf.seek(0)
                return pdf_buf.read()
        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(f"Invalid image data: {e}") from e


    def convert_text_to_pdf(self, text_data: bytes, filename: str = "document") -> bytes:
        if text_data is None:
            text_data = b""
        safe_name = _sanitize_filename(filename)
        pdf = FPDF()
        try:
            pdf.set_title(safe_name)
        except Exception:
            pass
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

        if len(text) > MAX_TEXT_CHARS:
            raise ValidationException(f"Text exceeds maximum of {MAX_TEXT_CHARS} characters")

        if not self._unicode_font:
            text = text.encode("latin-1", "replace").decode("latin-1")
        text = text.replace("\r", "")
        try:
            pdf.multi_cell(w=0, h=10, text=text)
        except Exception as e:
            raise ValidationException(f"Failed to render text to PDF: {e}") from e

        return _fpdf_output_bytes(pdf)

