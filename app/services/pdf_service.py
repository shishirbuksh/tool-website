import io

from fpdf import FPDF
from PIL import Image

from app.core.config import Settings


class PDFService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def convert_image_to_pdf(self, image_data: bytes, filename: str) -> bytes:
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        pdf_buf = io.BytesIO()
        image.save(pdf_buf, format="PDF", resolution=100.0)
        pdf_buf.seek(0)
        return pdf_buf.read()

    def convert_text_to_pdf(self, text_data: bytes) -> bytes:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)

        try:
            text = text_data.decode("utf-8")
        except UnicodeDecodeError:
            text = text_data.decode("latin-1")

        text = text.encode("latin-1", "replace").decode("latin-1")
        text = text.replace("\r", "")
        pdf.multi_cell(w=0, h=10, text=text)

        pdf_buf = io.BytesIO(pdf.output())
        pdf_buf.seek(0)
        return pdf_buf.read()
