"""XSS sanitization + security header guards."""

from app.core.sanitize import enhance_tables, sanitize_html


class TestSanitize:
    def test_script_stripped(self):
        out = str(sanitize_html('<script>alert(1)</script><p>hi</p>'))
        assert "<script" not in out
        assert "hi" in out

    def test_onerror_stripped(self):
        out = str(sanitize_html('<img src="x" onerror="alert(1)">'))
        assert "onerror" not in out

    def test_javascript_scheme_blocked(self):
        out = str(sanitize_html('<a href="javascript:alert(1)">x</a>'))
        assert "javascript:" not in out

    def test_data_text_html_blocked(self):
        out = str(sanitize_html('<a href="data:text/html,<script>alert(1)</script>">x</a>'))
        assert "data:text/html" not in out

    def test_allowed_link_kept_with_nofollow(self):
        out = str(sanitize_html('<a href="https://example.com">x</a>'))
        assert "https://example.com" in out
        assert "nofollow" in out

    def test_none_safe(self):
        assert "None" not in str(sanitize_html(None))

    def test_internal_relative_links_have_no_nofollow(self):
        out = str(sanitize_html('<a href="/tool/emi-calculator">x</a>'))
        assert 'href="/tool/emi-calculator"' in out
        assert "noopener" in out
        assert "nofollow" not in out

    def test_internal_fragment_links_have_no_nofollow(self):
        out = str(sanitize_html('<a href="#methodology">x</a>'))
        assert "nofollow" not in out


class TestArticleTables:
    def test_caption_and_scope_survive_sanitize(self):
        out = str(sanitize_html("<table><caption>Table — Demo</caption><thead><tr><th scope=\"col\">A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>"))
        assert "<caption>" in out
        assert 'scope="col"' in out

    def test_enhance_tables_adds_scope_and_wrapper(self):
        out = str(sanitize_html(enhance_tables("<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>")))
        assert out.count('scope="col"') == 2
        assert 'class="table-scroll"' in out
        assert 'role="region"' in out

    def test_enhance_tables_keeps_explicit_scope(self):
        out = enhance_tables('<table><tr><th scope="row">A</th></tr></table>')
        assert out.count("scope=") == 1
