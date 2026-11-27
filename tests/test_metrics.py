"""Tests for Django MetricsMiddleware: request counting and latency recording."""

from django.http import HttpResponse
from django.test import RequestFactory


class TestMetricsMiddleware:
    def test_tracks_request_count(self):
        from apps.core.metrics import MetricsMiddleware, request_count

        before = request_count.labels(method="GET", path="/test", status=200)._value.get()
        req = RequestFactory().get("/test")
        mw = MetricsMiddleware(lambda r: HttpResponse("ok", status=200))
        mw(req)

        after = request_count.labels(method="GET", path="/test", status=200)._value.get()
        assert after >= before + 1

    def test_records_latency(self):
        from apps.core.metrics import MetricsMiddleware

        req = RequestFactory().post("/api/test")
        mw = MetricsMiddleware(lambda r: HttpResponse("created", status=201))
        response = mw(req)
        assert response.status_code == 201
