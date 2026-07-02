"""Tests for ImageService: dependency gating, data validation, and error handling."""

import pytest

from app.core.exceptions import ServiceError, ValidationException
from app.services.image_service import ImageService


class TestImageService:
    def test_remove_background_missing_deps(self, settings):
        svc = ImageService(settings)
        with pytest.raises(ServiceError):
            svc.remove_background(b"fake-image-data")

    def test_remove_watermark_missing_deps(self, settings, monkeypatch):
        svc = ImageService(settings)
        def mock_get_cv2():
            raise ServiceError("OpenCV not installed")
        monkeypatch.setattr(svc, "_get_cv2", mock_get_cv2)
        with pytest.raises(ServiceError, match="OpenCV"):
            svc.remove_watermark(b"image-data", b"mask-data")

    def test_remove_watermark_invalid_data(self, settings):
        svc = ImageService(settings)
        with pytest.raises(ValidationException, match="must not be empty"):
            svc.remove_watermark(b"", b"")
