"""Tests for RequestIDMiddleware: header propagation, ID generation, and contextvar isolation."""

from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.core.log import _request_id_var, reset_request_id, set_request_id


class TestRequestIDMiddleware:
    @pytest.mark.asyncio
    async def test_adds_request_id_header(self):
        from app.core.middleware import RequestIDMiddleware

        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"X-Request-ID": "test-id-123"}
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        mock_call_next = AsyncMock(return_value=Response())

        middleware = RequestIDMiddleware(lambda: None)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-Request-ID"] == "test-id-123"
        assert _request_id_var.get() == ""

    @pytest.mark.asyncio
    async def test_generates_request_id_if_missing(self):
        from app.core.middleware import RequestIDMiddleware

        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {}
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        mock_call_next = AsyncMock(return_value=Response())

        middleware = RequestIDMiddleware(lambda: None)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-Request-ID"] is not None
        assert len(response.headers["X-Request-ID"]) > 0

    @pytest.mark.asyncio
    async def test_contextvar_isolation(self):
        token = set_request_id("outer-id")
        assert _request_id_var.get() == "outer-id"
        reset_request_id(token)
        assert _request_id_var.get() == ""


class TestSecurityHeadersMiddleware:
    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        from app.core.middleware import SecurityHeadersMiddleware

        mock_request = AsyncMock(spec=Request)
        mock_request.state = type("State", (), {})()
        mock_call_next = AsyncMock(return_value=Response())

        middleware = SecurityHeadersMiddleware(lambda: None)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "object-src 'none'" in response.headers["Content-Security-Policy"]
        assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin-allow-popups"
        assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
        assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"
        assert "browsing-topics=()" in response.headers["Permissions-Policy"]
        assert "Accept-Encoding" in response.headers["Vary"]


class TestCaseSensitiveRedirectMiddleware:
    @pytest.mark.asyncio
    async def test_relative_redirect_preserves_query(self):
        from app.core.middleware import CaseSensitiveRedirectMiddleware

        mock_url = type("Url", (), {"path": "/TOOL/Image-Compressor", "query": "source=header&ref=test"})()
        mock_request = AsyncMock(spec=Request)
        mock_request.url = mock_url
        mock_call_next = AsyncMock(return_value=Response())

        middleware = CaseSensitiveRedirectMiddleware(lambda: None)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 308
        assert response.headers["location"] == "/tool/image-compressor?source=header&ref=test"


class TestOriginCheckMiddleware:
    @pytest.mark.asyncio
    async def test_blocks_unauthorized_cross_origin_post(self):
        from app.core.middleware import OriginCheckMiddleware

        mock_request = AsyncMock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"Origin": "https://malicious-site.com"}
        mock_call_next = AsyncMock(return_value=Response())

        middleware = OriginCheckMiddleware(lambda: None)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 403
