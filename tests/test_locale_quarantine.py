"""End-to-end test verifying non-English paths redirect to English canonical routes
and no foreign sitemaps or hreflangs leak into English responses.
"""

from __future__ import annotations

import pytest


class TestQuarantineContract:
    def test_localized_pages_redirect_to_english(self, client):
        cases = [
            ("/de", "/"),
            ("/de/", "/"),
            ("/de/tools", "/tools"),
            ("/de/blog", "/blog"),
            ("/de/blog/calculators/emi-calculator-guide", "/blog/calculators/emi-calculator-guide"),
            ("/de/calculators", "/calculators"),
            ("/de/tool/emi-calculator", "/tool/emi-calculator"),
            ("/hi/tool/emi-calculator", "/tool/emi-calculator"),
            ("/es/tool/emi-calculator", "/tool/emi-calculator"),
            ("/fr/tool/emi-calculator", "/tool/emi-calculator"),
        ]
        for path, expected_location in cases:
            r = client.get(path, follow_redirects=False)
            assert r.status_code == 301, f"{path} did not 301 redirect"
            assert r.headers.get("location") == expected_location, f"{path} redirected to wrong location"

    def test_localized_sitemaps_are_not_published(self, client):
        for loc in ("hi", "es", "fr", "de"):
            assert client.get(f"/sitemap-{loc}.xml").status_code == 404, loc
        index = client.get("/sitemap-index.xml").text
        for loc in ("hi", "es", "fr", "de"):
            assert f"sitemap-{loc}.xml" not in index, loc
        robots = client.get("/robots.txt").text
        for loc in ("hi", "es", "fr", "de"):
            assert f"sitemap-{loc}.xml" not in robots, loc

    def test_english_page_does_not_advertise_quarantined_alternates(self, client):
        r = client.get("/tool/emi-calculator")
        assert r.status_code == 200
        assert "X-Robots-Tag" not in r.headers
        assert 'hreflang="en"' in r.text
        assert 'hreflang="x-default"' in r.text
        for loc in ("hi", "es", "fr", "de"):
            assert f'hreflang="{loc}"' not in r.text, loc
