"""Rendered-UI tests for English calculator chrome.

Ensures calculators render proper English labels, accessible chrome,
and that legacy localized calculator URLs 301 redirect to canonical English tools.
"""

from __future__ import annotations

import html as html_lib
import re

import pytest

ENGLISH_TOOLS = (
    "/tool/emi-calculator",
    "/tool/mortgage-overpayment-calculator",
    "/tool/debt-calculator",
    "/tool/loan-affordability-calculator",
)


def _visible_text(html: str) -> str:
    """Strip scripts, styles and tags, then unescape visible text."""
    region = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    region = re.sub(r"<style.*?</style>", " ", region, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", region)
    return html_lib.unescape(re.sub(r"\s+", " ", text))


@pytest.mark.parametrize("path", ENGLISH_TOOLS)
def test_english_calculator_renders_successfully(client, path):
    response = client.get(path)
    assert response.status_code == 200, path
    assert 'lang="en"' in response.text
    assert "StoryBrain AI" in response.text
    assert ">>" not in response.text


def test_emi_calculator_english_chrome(client):
    response = client.get("/tool/emi-calculator")
    assert response.status_code == 200
    text = _visible_text(response.text)
    assert "Loan Details" in text or "Loan Amount" in text
    assert "Monthly EMI" in text or "EMI" in text
    assert "Payment Summary" in text or "Total Payment" in text


def test_navbar_and_footer_english_chrome(client):
    response = client.get("/tool/emi-calculator")
    assert response.status_code == 200
    html = response.text
    assert ">Home<" in html
    assert ">All Tools<" in html
    assert ">Categories<" in html
    assert ">Blog<" in html


def test_search_dialog_english_messages(client):
    response = client.get("/tool/emi-calculator")
    assert response.status_code == 200
    raw = html_lib.unescape(response.text)
    assert 'data-msg-empty="Type to search tools..."' in raw or 'search.empty' not in raw
    assert 'aria-label="Search tools"' in raw or 'aria-label="Search"' in raw


@pytest.mark.parametrize(
    ("path", "canonical"),
    [
        ("/de/tool/emi-calculator", "/tool/emi-calculator"),
        ("/es/tool/emi-calculator", "/tool/emi-calculator"),
        ("/fr/tool/emi-calculator", "/tool/emi-calculator"),
        ("/hi/tool/emi-calculator", "/tool/emi-calculator"),
        ("/de/tool/mortgage-overpayment-calculator", "/tool/mortgage-overpayment-calculator"),
        ("/es/tool/debt-calculator", "/tool/debt-calculator"),
        ("/de/tool/loan-affordability-calculator", "/tool/loan-affordability-calculator"),
    ],
)
def test_legacy_localized_calculator_urls_redirect(client, path, canonical):
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 301
    assert response.headers.get("location") == canonical
