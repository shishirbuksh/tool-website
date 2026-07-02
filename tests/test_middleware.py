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
