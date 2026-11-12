"""Tests for English calculator UI consistency, badges, accessibility labels, and legacy redirects."""

import pytest


class TestEnglishCalculatorUI:
    @pytest.mark.parametrize(
        ("path", "expected_snippet"),
        [
            ("/tool/emi-calculator", 'INTL_LOCALE = "en-US"'),
            ("/tool/debt-calculator", 'INTL_LOCALE = "en-US"'),
            ("/tool/mortgage-overpayment-calculator", 'currentCurrency = "USD"'),
            ("/tool/gst-calculator", "₹1,000.00"),
            ("/tool/fd-calculator", "$"),
        ],
    )
    def test_calculator_english_defaults(self, client, path, expected_snippet):
        resp = client.get(path)
        assert resp.status_code == 200
        assert expected_snippet in resp.text
        assert "if loc ==" not in resp.text

    @pytest.mark.parametrize(
        ("path", "badge_text"),
        [
            ("/tool/qr-generator", "QR Generator"),
            ("/tool/unit-converter", "Productivity"),
            ("/tool/word-counter", "Writer"),
            ("/tool/gst-calculator", "Calculator"),
        ],
    )
    def test_tool_hero_badge_not_generic_all_tools(self, client, path, badge_text):
        resp = client.get(path)
        assert resp.status_code == 200
        assert f"<span>{badge_text}</span>" in resp.text

    def test_crypto_tax_calculator_clean_aria_labels(self, client):
        resp = client.get("/tool/crypto-tax-calculator")
        assert resp.status_code == 200
        for bad in ("Taxcostbasis", "Taxproceeds", "Taxincome"):
            assert bad not in resp.text
        assert 'aria-label="Purchase Price / Cost Basis"' in resp.text

    @pytest.mark.parametrize(
        ("src", "expected"),
        [
            ("/de/tool/emi-calculator", "/tool/emi-calculator"),
            ("/es/tool/emi-calculator", "/tool/emi-calculator"),
            ("/fr/tool/emi-calculator", "/tool/emi-calculator"),
            ("/hi/tool/emi-calculator", "/tool/emi-calculator"),
        ],
    )
    def test_legacy_calculator_301_redirect(self, client, src, expected):
        resp = client.get(src, follow_redirects=False)
        assert resp.status_code == 301
        assert resp.headers["location"] == expected
