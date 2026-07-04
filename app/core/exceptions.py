"""Application exception hierarchy and FastAPI exception handler registration."""

import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from starlette import status

from app.core.log import get_logger, get_request_id

templates = None
_templates_lock = threading.Lock()

logger = get_logger(__name__)

# Sentinel to prevent recursive error handling when templates fail
_recursion_guard = threading.local()


def _with_request_id(content: dict) -> dict:
    rid = get_request_id()
    if rid:
        content["request_id"] = rid
    return content


class AppException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class ValidationException(AppException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


class ServiceError(AppException):
    def __init__(self, detail: str = "Service error"):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _should_render_html(request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept


def _error_html_response(request, status_code: int, detail: str) -> HTMLResponse:
    if getattr(_recursion_guard, "in_handler", False):
        return HTMLResponse(
            content=f"<html><body><h1>{status_code}</h1><p>{detail}</p></body></html>",
            status_code=status_code,
        )
    _recursion_guard.in_handler = True
    try:
        if templates is None:
            return HTMLResponse(
                content=f"<html><body><h1>{status_code}</h1><p>{detail}</p></body></html>",
                status_code=status_code,
            )
        return templates.TemplateResponse(
            request=request,
            name="pages/404.html",
            context={"status_code": status_code, "detail": detail},
            status_code=status_code,
        )
    finally:
        _recursion_guard.in_handler = False


def _app_exception_handler(request, exc: AppException):
    if _should_render_html(request):
        return _error_html_response(request, exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_with_request_id({"detail": exc.detail}),
    )


def _http_exception_handler(request, exc: HTTPException):
    if _should_render_html(request):
        return _error_html_response(request, exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_with_request_id({"detail": exc.detail}),
    )


def _generic_exception_handler(request, exc: Exception):
    logger.exception("Unhandled exception")
    if _should_render_html(request):
        return _error_html_response(request, status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_with_request_id({"detail": "Internal server error"}),
    )


def register_exception_handlers(app: FastAPI):
    global templates
    if templates is None:
        with _templates_lock:
            if templates is None:
                from app.api.routes.pages import templates as page_templates  # noqa: PLC0415
                templates = page_templates
    app.add_exception_handler(AppException, _app_exception_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)
