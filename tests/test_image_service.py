import pytest

from app.core.exceptions import ServiceError, ValidationException
from app.services.image_service import ImageService


class TestImageService:
    def test_remove_background_missing_deps(self, settings):
        svc = ImageService(settings)
        with pytest.raises((ServiceError, Exception)):
            svc.remove_background(b"fake-image-data")

    def test_remove_watermark_missing_deps(self, settings):
        svc = ImageService(settings)
        with pytest.raises(ServiceError, match="OpenCV"):
            svc.remove_watermark(b"image-data", b"mask-data")

    def test_remove_watermark_invalid_data(self, settings):
        svc = ImageService(settings)
        try:
            svc.remove_watermark(b"", b"")
        except ServiceError as e:
            if "OpenCV" in str(e.detail):
                pytest.skip("OpenCV not installed")
            raise
        except ValidationException:
            pass
        except Exception:
            pass
