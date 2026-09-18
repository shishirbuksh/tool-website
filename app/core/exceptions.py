"""Application exception hierarchy and FastAPI exception handler registration."""

import contextvars
import html
import threading

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette import status

from app.core.log import get_logger, get_request_id

templates = None
_templates_lock = threading.Lock()

logger = get_logger(__name__)

# Sentinel to prevent recursive error handling when templates fail.
# ContextVar (not threading.local) so async tasks / context propagation are safe.
_recursion_guard: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "exc_recursion_guard", default=False
)


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


_ERROR_CACHE_CONTROL = {"Cache-Control": "no-cache, no-store, must-revalidate"}


def _error_html_response(request, status_code: int, detail: str) -> HTMLResponse:
    safe_detail = html.escape(str(detail))
    if _recursion_guard.get():
        return HTMLResponse(
            content=f"<html><body><h1>{status_code}</h1><p>{safe_detail}</p></body></html>",
            status_code=status_code,
            headers=_ERROR_CACHE_CONTROL,
        )
    token = _recursion_guard.set(True)
    try:
        if templates is None:
            return HTMLResponse(
                content=f"<html><body><h1>{status_code}</h1><p>{safe_detail}</p></body></html>",
                status_code=status_code,
                headers=_ERROR_CACHE_CONTROL,
            )
        # Use a dedicated 500 template for server errors; 404 template otherwise.
        template_name = "pages/500.html" if status_code >= 500 else "pages/404.html"
        try:
            return templates.TemplateResponse(
                request=request,
                name=template_name,
                context={"status_code": status_code, "detail": detail},
                status_code=status_code,
                headers=_ERROR_CACHE_CONTROL,
            )
        except Exception:
            logger.exception("Error template %s failed, using fallback", template_name)
            # Fall back to the other template, then to a generic message.
            fallback = "pages/404.html" if template_name != "pages/404.html" else None
            if fallback is not None:
                try:
                    return templates.TemplateResponse(
                        request=request,
                        name=fallback,
                        context={"status_code": status_code, "detail": detail},
                        status_code=status_code,
                        headers=_ERROR_CACHE_CONTROL,
                    )
                except Exception:
                    logger.exception("Fallback error template failed")
            if status_code >= 500:
                safe_detail = "Internal server error"
            return HTMLResponse(
                content=f"<html><body><h1>{status_code}</h1><p>{safe_detail}</p></body></html>",
                status_code=status_code,
                headers=_ERROR_CACHE_CONTROL,
            )
    finally:
        _recursion_guard.reset(token)


def _app_exception_handler(request, exc: AppException):
    if _should_render_html(request):
        return _error_html_response(request, exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_with_request_id({"detail": exc.detail}),
        headers=_ERROR_CACHE_CONTROL,
    )


def _http_exception_handler(request, exc: HTTPException):
    if _should_render_html(request):
        return _error_html_response(request, exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_with_request_id({"detail": exc.detail}),
        headers=_ERROR_CACHE_CONTROL,
    )


def _generic_exception_handler(request, exc: Exception):
    logger.exception("Unhandled exception")
    if _should_render_html(request):
        return _error_html_response(request, status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_with_request_id({"detail": "Internal server error"}),
        headers=_ERROR_CACHE_CONTROL,
    )


async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    if _should_render_html(request):
        return _error_html_response(request, status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc.errors()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_with_request_id({"detail": jsonable_encoder(exc.errors(), custom_encoder={Exception: str})}),
        headers=_ERROR_CACHE_CONTROL,
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
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)
