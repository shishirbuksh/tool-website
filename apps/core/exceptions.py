"""Application exception hierarchy following django-python patterns."""

from __future__ import annotations


class AppException(Exception):
    def __init__(self, detail: str, status_code: int = 500):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail=detail, status_code=404)


class ValidationException(AppException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(detail=detail, status_code=422)


class ServiceError(AppException):
    def __init__(self, detail: str = "Service error", status_code: int = 500):
        super().__init__(detail=detail, status_code=status_code)
