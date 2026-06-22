import pytest
from starlette import status

from app.core.exceptions import AppException, NotFoundException, ValidationException, ServiceError


class TestExceptions:
    def test_app_exception_defaults(self):
        exc = AppException(detail="something broke")
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.detail == "something broke"

    def test_not_found_exception(self):
        exc = NotFoundException()
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.detail == "Resource not found"

    def test_not_found_custom_detail(self):
        exc = NotFoundException(detail="Custom missing")
        assert exc.detail == "Custom missing"

    def test_validation_exception(self):
        exc = ValidationException()
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert exc.detail == "Validation error"

    def test_service_error(self):
        exc = ServiceError()
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.detail == "Service error"

    def test_inheritance_chain(self):
        assert issubclass(NotFoundException, AppException)
        assert issubclass(ValidationException, AppException)
        assert issubclass(ServiceError, AppException)
        assert issubclass(AppException, Exception)