"""Blog engine integration tests: index, pillar, post, 404s, CSP nonce, no-cache headers."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 80))


class TestBlogPages:
    def test_blog_index_200(self):
        resp = client.get("/blog")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_blog_pillar_200(self):
        resp = client.get("/blog/calculators")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_blog_post_200(self):
        resp = client.get("/blog/calculators/emi-calculator-guide")
        assert resp.status_code == 200
        assert "EMI Calculator Guide" in resp.text

    def test_blog_post_404_unknown_slug(self):
        resp = client.get("/blog/calculators/no-such-post-xyz")
        assert resp.status_code == 404

    def test_blog_pillar_404(self):
        resp = client.get("/blog/no-such-pillar-xyz")
        assert resp.status_code == 404

    def test_blog_post_404_wrong_pillar(self):
        resp = client.get("/blog/developer-tools/emi-calculator-guide")
        assert resp.status_code == 404

    def test_blog_csp_nonce_present(self):
        resp = client.get("/blog/calculators/emi-calculator-guide")
        assert resp.status_code == 200
        assert 'nonce="' in resp.text
        csp = resp.headers.get("content-security-policy", "")
        assert "nonce-" in csp

    def test_blog_no_cache_header(self):
        for path in ("/blog", "/blog/calculators", "/blog/calculators/emi-calculator-guide"):
            resp = client.get(path)
            assert resp.status_code == 200
            cc = resp.headers.get("cache-control", "")
            assert "private" in cc
            assert "no-cache" in cc
