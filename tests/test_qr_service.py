from app.services.qr_service import QRService


class TestQRService:
    def test_generate_default(self, settings):
        svc = QRService(settings)
        result = svc.generate("https://example.com")
        assert isinstance(result, bytes)
        assert len(result) > 100
        assert result[:4] == b"\x89PNG"

    def test_generate_with_colors(self, settings):
        svc = QRService(settings)
        result = svc.generate("test", fg_color="blue", bg_color="yellow")
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    def test_generate_error_correction_levels(self, settings):
        svc = QRService(settings)
        for level in ["L", "M", "Q", "H"]:
            result = svc.generate("data", error_correction=level)
            assert result[:4] == b"\x89PNG", f"Failed for EC level {level}"

    def test_generate_empty_data(self, settings):
        svc = QRService(settings)
        result = svc.generate("")
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"
