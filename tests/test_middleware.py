from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import Response


class TestRequestIDMiddleware:
    @pytest.mark.asyncio
    async def test_adds_request_id_header(self):
        from app.core.log import get_request_id_filter
        from app.core.middleware import RequestIDMiddleware

        filt = get_request_id_filter()

        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"X-Request-ID": "test-id-123"}
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        mock_call_next = AsyncMock(return_value=Response())

        middleware = RequestIDMiddleware(lambda: None)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-Request-ID"] == "test-id-123"
        assert filt._request_id == "test-id-123"

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
