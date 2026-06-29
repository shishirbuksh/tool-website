"""Tests for PDFService: image-to-PDF, text-to-PDF, and edge cases (empty, unicode)."""

import io

from PIL import Image

from app.services.pdf_service import PDFService


class TestPDFService:
    def test_convert_image_to_pdf_returns_bytes(self, settings):
        svc = PDFService(settings)
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        img_data = buf.read()

        result = svc.convert_image_to_pdf(img_data, "test.png")
        assert isinstance(result, bytes)
        assert len(result) > 50
        assert result[:5] == b"%PDF-"

    def test_convert_image_to_pdf_small_image(self, settings):
        svc = PDFService(settings)
        img = Image.new("RGB", (1, 1), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        img_data = buf.read()

        result = svc.convert_image_to_pdf(img_data, "test.png")
        assert result[:5] == b"%PDF-"

    def test_convert_text_to_pdf_returns_bytes(self, settings):
        svc = PDFService(settings)
        result = svc.convert_text_to_pdf(b"Hello World")
        assert isinstance(result, bytes)
        assert len(result) > 50
        assert result[:5] == b"%PDF-"

    def test_convert_text_to_pdf_multiline(self, settings):
        svc = PDFService(settings)
        text = "Line 1\nLine 2\nLine 3"
        result = svc.convert_text_to_pdf(text.encode("utf-8"))
        assert result[:5] == b"%PDF-"

    def test_convert_text_to_pdf_empty(self, settings):
        svc = PDFService(settings)
        result = svc.convert_text_to_pdf(b"")
        assert result[:5] == b"%PDF-"

    def test_convert_text_to_pdf_unicode(self, settings):
        svc = PDFService(settings)
        result = svc.convert_text_to_pdf("ñooño".encode())
        assert result[:5] == b"%PDF-"
