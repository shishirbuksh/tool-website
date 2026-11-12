"""Tests verifying legacy /hi, /es, /fr, /de routes issue HTTP 301 redirects to English canonical URLs."""

import pytest


class TestLegacyLocaleRedirects:
    @pytest.mark.parametrize(
        ("src", "expected"),
        [
            ("/hi", "/"),
            ("/es", "/"),
            ("/fr", "/"),
            ("/de", "/"),
            ("/hi/", "/"),
            ("/de/", "/"),
            ("/es/tools", "/tools"),
            ("/fr/blog", "/blog"),
            ("/de/tool/emi-calculator", "/tool/emi-calculator"),
            ("/hi/tool/fd-calculator?foo=1", "/tool/fd-calculator?foo=1"),
            ("/es/offline", "/offline"),
            ("/de/student-tools", "/student-tools"),
        ],
    )
    def test_legacy_locale_paths_redirect_301(self, client, src, expected):
        resp = client.get(src, follow_redirects=False)
        assert resp.status_code == 301
        assert resp.headers["location"] == expected

    def test_404_has_no_broken_hub_links(self, client):
        resp = client.get("/this-page-does-not-exist-404", headers={"Accept": "text/html"})
        assert resp.status_code == 404
        assert "/hub/" not in resp.text
        assert "/calculators" in resp.text
        assert "/student-tools" in resp.text
