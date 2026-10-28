"""Rendered-UI regression tests for localized calculator chrome.

These tests protect the release gate for DE/ES wave 1a: a localized page must
not fall back to English/US-centric calculator labels, currency symbols, or
finance assumptions. They intentionally inspect the rendered HTML (not just
the translation table) so a template that forgets ``tr()`` fails.
"""

from __future__ import annotations

import html as html_lib
import re

import pytest

from app.core.i18n import t as tr

# English chrome that must never appear on a localized calculator page.
FORBIDDEN_CHROME = (
    "Loan Details",
    "Payment Summary",
    "Monthly EMI",
    "Total Payment",
    "Prepayment Plan",
    "Extra Monthly Payment",
    "Interest Saved",
    "Time Reduced",
    "No calculations yet",
    "Loan Comparison",
    "Rate vs Tenure",
    "Your Mortgage",
    "Loan Balance",
    "Annual Interest Rate",
    "Quick Scenario Picks",
    "Without Overpayment",
    "With Overpayment",
    "Amortization Schedule",
    "Start Balance",
    "End Balance",
    "Your Debts",
    "Payoff Summary",
    "Method Comparison",
    "Debt-Free By",
    "Best Method",
    "Annual Income",
    "Monthly Debt Payments",
    "Down Payment",
    "Property Tax",
    "Home Insurance",
    "Affordability Scenarios",
    "Max Loan Amount",
    "Max Home Price",
    "Total Monthly Cost",
    "Tax Deduction",
    "Equity & Net Worth",
)

PAGES = {
    "de": {
        "/de/tool/emi-calculator": ("Kreditbetrag", "Zahlungsübersicht", "Monatliche Rate"),
        "/de/tool/mortgage-overpayment-calculator": (
            "Ihre Finanzierung",
            "Restschuld",
            "Sondertilgung",
        ),
        "/de/tool/debt-calculator": ("Ihre Schulden", "Tilgungsübersicht", "Schneeball"),
        "/de/tool/loan-affordability-calculator": (
            "Nettoeinkommen pro Monat",
            "Kaufnebenkosten",
            "Zinsbindung",
        ),
    },
    "es": {
        "/es/tool/emi-calculator": (
            "Importe del préstamo",
            "Resumen de pagos",
            "Cuota mensual",
        ),
        "/es/tool/mortgage-overpayment-calculator": (
            "Tu hipoteca",
            "Capital pendiente",
            "Amortización extra",
        ),
        "/es/tool/debt-calculator": ("Tus deudas", "Resumen de pago", "Bola de nieve"),
        "/es/tool/loan-affordability-calculator": (
            "Ingresos netos mensuales",
            "Gastos de compra",
            "Periodo fijo",
        ),
    },
}


def _visible_text(html: str) -> str:
    """Strip scripts, styles and tags, then unescape visible text."""
    region = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    region = re.sub(r"<style.*?</style>", " ", region, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", region)
    return html_lib.unescape(re.sub(r"\s+", " ", text))


def _calculator_text(html: str, locale: str) -> str:
    """Visible text from <main> up to the localized SEO/FAQ block."""
    start = html.find('<main id="main-content"')
    assert start != -1, "missing main content"
    faq_title = tr("tool.faq_title", locale)
    faq_at = html.find(faq_title, start)
    end = faq_at if faq_at != -1 else html.find("</main>", start)
    assert end != -1, "missing main end"
    return _visible_text(html[start:end])


def _footer_text(html: str) -> str:
    """Visible text of the last site footer on the page."""
    start = html.rfind("<footer")
    assert start != -1, "missing site footer"
    end = html.find("</footer>", start)
    assert end != -1, "unclosed site footer"
    return _visible_text(html[start:end])


@pytest.mark.parametrize(("locale", "path"), [(loc, path) for loc, pages in PAGES.items() for path in pages])
def test_localized_calculator_chrome_is_not_english(client, locale, path):
    response = client.get(path)
    assert response.status_code == 200, path
    text = _calculator_text(response.text, locale)
    for marker in PAGES[locale][path]:
        assert marker in text, f"{path} missing localized marker {marker!r}"
    for phrase in FORBIDDEN_CHROME:
        assert phrase not in text, f"{path} leaks English chrome {phrase!r}"


@pytest.mark.parametrize("locale", ["de", "es"])
def test_localized_calculators_use_euro_not_dollars(client, locale):
    for path in PAGES[locale]:
        response = client.get(path)
        assert response.status_code == 200, path
        text = _calculator_text(response.text, locale)
        assert "$" not in text, f"{path} renders a dollar sign"
        assert "€" in text, f"{path} does not render a euro sign"


@pytest.mark.parametrize("locale", ["de", "es"])
def test_navbar_categories_are_localized(client, locale):
    response = client.get(f"/{locale}/tool/emi-calculator")
    assert response.status_code == 200
    html = response.text
    assert f">{tr('nav.categories', locale)}<" in html
    # Exact link text (not substring) so a related tool description cannot
    # accidentally satisfy or fail the assertion.
    assert ">AI &amp; Crypto<" not in html
    assert ">Calculators<" not in html
    assert f">{tr('footer.categories', locale)}<" in html


FOOTER_POPULAR_KEYS = (
    "footer.tool.qr",
    "footer.tool.emi",
    "footer.tool.password",
    "footer.tool.crypto",
    "footer.tool.background",
    "footer.tool.invoice",
)

FOOTER_ENGLISH_POPULAR = (
    "QR Generator",
    "Password Generator",
    "Crypto Price Prediction",
    "Image Background Remover",
    "Invoice Generator",
)


@pytest.mark.parametrize("locale", ["de", "es", "fr", "hi"])
def test_footer_popular_tools_and_methodology_are_localized(client, locale):
    """Shared footer and methodology/feedback chrome must follow the locale.

    These blocks are rendered on every tool page, so an English fallback here
    would leak onto all 10 wave-1a URLs even when the calculator itself is
    localized.
    """
    path = f"/{locale}/tool/emi-calculator"
    response = client.get(path)
    assert response.status_code == 200

    footer = _footer_text(response.text)
    for key in FOOTER_POPULAR_KEYS:
        expected = tr(key, locale)
        assert expected in footer, f"{path} footer missing {key}={expected!r}"
    for english in FOOTER_ENGLISH_POPULAR:
        assert english not in footer, f"{path} footer leaks English {english!r}"

    page = _visible_text(response.text)
    for key in ("tool.methodology_title", "tool.feedback_question", "tool.feedback_thanks"):
        expected = tr(key, locale)
        assert expected in page, f"{path} missing {key}={expected!r}"
    assert "Methodology & feedback" not in page
    assert "Was this tool helpful?" not in page

    # Shared chrome accessibility labels must follow the locale too. Unescape
    # first so Jinja's apostrophe entities (e.g. fr "Fil d&#39;Ariane") match.
    raw = html_lib.unescape(response.text)
    for english_aria in (
        'aria-label="Breadcrumb"',
        'aria-label="Mobile navigation"',
        'aria-label="Home"',
        'aria-label="All Tools"',
        'aria-label="Search"',
        'aria-label="Theme"',
        'aria-label="StoryBrain AI Home"',
        'aria-label="Cookie consent"',
    ):
        assert english_aria not in raw, f"{path} leaks {english_aria}"
    for key in ("nav.breadcrumb", "nav.mobile", "nav.all_tools", "nav.search"):
        expected = tr(key, locale)
        assert f'aria-label="{expected}"' in raw, f"{path} missing aria-label {key}={expected!r}"
    assert tr("cookie.title", locale) in page


@pytest.mark.parametrize(
    ("locale", "native_markers"),
    [
        ("de", ("Kaufnebenkosten", "Zinsbindung", "Konservativ (35 %)", "Moderat (40 %)")),
        ("es", ("Gastos de compra", "Periodo fijo", "Conservador (35 %)", "Moderado (40 %)")),
    ],
)
def test_de_es_affordability_is_native_not_us_model(client, locale, native_markers):
    path = f"/{locale}/tool/loan-affordability-calculator"
    response = client.get(path)
    assert response.status_code == 200
    text = _calculator_text(response.text, locale)
    for marker in native_markers:
        assert marker in text, f"{path} missing native marker {marker!r}"
    for us_term in ("PMI", "HOA", "DTI", "Property Tax", "Annual Income", "28%", "36%", "43%"):
        assert us_term not in text, f"{path} still renders US model term {us_term!r}"
    assert 'id="affForm"' in response.text


@pytest.mark.parametrize(
    ("locale", "path", "field", "expected"),
    [
        ("de", "/de/tool/emi-calculator", "emAmount", "20000"),
        ("es", "/es/tool/emi-calculator", "emAmount", "15000"),
        ("de", "/de/tool/mortgage-overpayment-calculator", "loanBalance", "300000"),
        ("es", "/es/tool/mortgage-overpayment-calculator", "loanBalance", "200000"),
        ("de", "/de/tool/debt-calculator", "extraPayment", "100"),
        ("es", "/es/tool/debt-calculator", "extraPayment", "100"),
        ("de", "/de/tool/loan-affordability-calculator", "affIncome", "3200"),
        ("es", "/es/tool/loan-affordability-calculator", "affIncome", "2400"),
    ],
)
def test_localized_calculator_defaults_are_locale_specific(client, locale, path, field, expected):
    response = client.get(path)
    assert response.status_code == 200
    pattern = rf'id="{re.escape(field)}"[^>]*value="{re.escape(expected)}"'
    assert re.search(pattern, response.text), f"{path} missing {field}={expected}"


@pytest.mark.parametrize("locale", ["de", "es"])
def test_mortgage_currency_selector_puts_euro_first(client, locale):
    path = f"/{locale}/tool/mortgage-overpayment-calculator"
    response = client.get(path)
    assert response.status_code == 200
    options = re.findall(r'<option value="([A-Z]{3})"', response.text)
    assert options, f"{path} has no currency options"
    assert options[0] == "EUR", f"{path} currency selector starts with {options[0]}"


@pytest.mark.parametrize(
    "path",
    [
        "/de/tool/emi-calculator",
        "/es/tool/emi-calculator",
        "/de/tool/mortgage-overpayment-calculator",
        "/es/tool/mortgage-overpayment-calculator",
        "/de/tool/debt-calculator",
        "/es/tool/debt-calculator",
        "/de/tool/loan-affordability-calculator",
        "/es/tool/loan-affordability-calculator",
    ],
)
def test_no_stray_button_markup(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert ">>" not in response.text, f"{path} renders stray '>>' markup"
