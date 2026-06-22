import pytest
from starlette.responses import Response


class TestMetricsMiddleware:
    @pytest.mark.asyncio
    async def test_tracks_request_count(self):
        from app.core.metrics import MetricsMiddleware, request_count

        before = request_count.labels(method="GET", path="/test", status=200)._value.get()

        mock_request = type("Req", (), {"method": "GET", "url": type("Url", (), {"path": "/test"})()})()

        async def ok_handler(_):
            return Response(status_code=200)

        mw = MetricsMiddleware(lambda: None)
        await mw.dispatch(mock_request, ok_handler)

        after = request_count.labels(method="GET", path="/test", status=200)._value.get()
        assert after >= before + 1

    @pytest.mark.asyncio
    async def test_records_latency(self):
        from app.core.metrics import MetricsMiddleware

        mock_request = type("Req", (), {"method": "POST", "url": type("Url", (), {"path": "/api/test"})()})()

        async def fast_handler(_):
            return Response(status_code=201)

        mw = MetricsMiddleware(lambda: None)
        response = await mw.dispatch(mock_request, fast_handler)
        assert response.status_code == 201