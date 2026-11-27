"""Tests for Django middlewares: RequestID, SecurityHeaders, OriginCheck, CleanQuery, TrailingSlash, CaseSensitive."""

from django.http import HttpResponse
from django.test import RequestFactory


class TestRequestIDMiddleware:
    def test_adds_request_id_header(self):
        from apps.core.log import _request_id_var
        from apps.core.middleware import RequestIDMiddleware

        req = RequestFactory().get("/test", HTTP_X_REQUEST_ID="test-id-123")
        mw = RequestIDMiddleware(lambda r: HttpResponse("ok"))
        response = mw(req)

        assert response["X-Request-ID"] == "test-id-123"
        assert _request_id_var.get() == ""

    def test_generates_request_id_if_missing(self):
        from apps.core.middleware import RequestIDMiddleware

        req = RequestFactory().get("/test")
        mw = RequestIDMiddleware(lambda r: HttpResponse("ok"))
        response = mw(req)

        assert response.get("X-Request-ID")
        assert len(response["X-Request-ID"]) > 0

    def test_contextvar_isolation(self):
        from apps.core.log import _request_id_var, reset_request_id, set_request_id

        token = set_request_id("outer-id")
        assert _request_id_var.get() == "outer-id"
        reset_request_id(token)
        assert _request_id_var.get() == ""


class TestSecurityHeadersMiddleware:
    def test_security_headers_present(self):
        from apps.core.middleware import SecurityHeadersMiddleware

        req = RequestFactory().get("/test")
        mw = SecurityHeadersMiddleware(lambda r: HttpResponse("ok"))
        response = mw(req)

        assert "object-src 'none'" in response["Content-Security-Policy"]
        assert response["Cross-Origin-Opener-Policy"] == "same-origin-allow-popups"
        assert response["Cross-Origin-Resource-Policy"] == "same-origin"
        assert response["X-Permitted-Cross-Domain-Policies"] == "none"
        assert response["X-Page-Speed"] == "off"
        assert "camera=()" in response["Permissions-Policy"]
        assert "Accept-Encoding" in response["Vary"]


class TestCaseSensitiveRedirectMiddleware:
    def test_relative_redirect_preserves_query(self):
        from apps.core.middleware import CaseSensitiveRedirectMiddleware

        req = RequestFactory().get("/TOOL/Image-Compressor?source=header&ref=test")
        mw = CaseSensitiveRedirectMiddleware(lambda r: HttpResponse("ok"))
        response = mw(req)

        assert response.status_code == 301
        assert response["Location"] == "/tool/image-compressor?source=header&ref=test"


class TestOriginCheckMiddleware:
    def test_blocks_unauthorized_cross_origin_post(self):
        from apps.core.middleware import OriginCheckMiddleware

        req = RequestFactory().post("/api/track", HTTP_ORIGIN="https://malicious-site.com")
        mw = OriginCheckMiddleware(lambda r: HttpResponse("ok"))
        response = mw(req)

        assert response.status_code == 403


class TestCleanQueryMiddleware:
    def test_strips_pagespeed_junk(self):
        from apps.core.middleware import CleanQueryMiddleware

        req = RequestFactory().get("/tool/calculator?pagespeed=noscript&valid=1")
        mw = CleanQueryMiddleware(lambda r: HttpResponse("ok"))
        response = mw(req)

        assert response.status_code == 301
        assert response["Location"] == "/tool/calculator?valid=1"

    def test_preserves_marketing_utm_and_gclid_by_default(self):
        from apps.core.middleware import CleanQueryMiddleware

        req = RequestFactory().get("/tool/calculator?utm_source=twitter&gclid=123")
        mw = CleanQueryMiddleware(lambda r: HttpResponse("ok"))
        response = mw(req)

        assert response.status_code == 200


class TestTrailingSlashRedirectMiddleware:
    def test_trailing_slash_redirects_301_relative(self):
        from apps.core.middleware import TrailingSlashRedirectMiddleware

        called = False

        def inner(_r):
            nonlocal called
            called = True
            return HttpResponse("ok")

        req = RequestFactory().get("/tools/")
        mw = TrailingSlashRedirectMiddleware(inner)
        response = mw(req)

        assert response.status_code == 301
        assert response["Location"] == "/tools"
        assert not called

    def test_trailing_slash_lowercases_and_preserves_query(self):
        from apps.core.middleware import TrailingSlashRedirectMiddleware

        req = RequestFactory().head("/TOOL/Image-Compressor/?q=webp&ref=nav")
        mw = TrailingSlashRedirectMiddleware(lambda r: HttpResponse("ok"))
        response = mw(req)

        assert response.status_code == 301
        assert response["Location"] == "/tool/image-compressor?q=webp&ref=nav"

    def test_root_and_static_do_not_redirect(self):
        from apps.core.middleware import TrailingSlashRedirectMiddleware

        mw = TrailingSlashRedirectMiddleware(lambda r: HttpResponse("ok"))
        for path in ("/", "/static/css/"):
            req = RequestFactory().get(path)
            response = mw(req)
            assert response.status_code == 200
            assert "Location" not in response

    def test_post_to_trailing_slash_does_not_redirect(self):
        from apps.core.middleware import TrailingSlashRedirectMiddleware

        mw = TrailingSlashRedirectMiddleware(lambda r: HttpResponse("ok"))
        req = RequestFactory().post("/api/track/")
        response = mw(req)
        assert response.status_code == 200
        assert "Location" not in response
