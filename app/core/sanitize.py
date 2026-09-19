"""Shared HTML sanitization — single source of truth for Jinja `sanitize` filter.

Strict allowlist on top of nh3 (ammonia) defaults so upstream version drift
can't widen XSS surface. Used by pages.py + blog.py.
"""

import nh3
from markupsafe import Markup

_ALLOWED_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "caption",
    "code",
    "dd",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}

_ALLOWED_ATTRIBUTES = {
    # NOTE: do NOT allow "rel" here — nh3 sets rel via link_rel param; allowing both raises ValueError.
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height", "loading"},
    "div": {"class", "role", "aria-label", "tabindex"},
    "span": {"class"},
    "p": {"class"},
    "code": {"class"},
    "pre": {"class"},
    "table": {"class"},
    "th": {"scope", "colspan", "rowspan", "class"},
    "td": {"scope", "colspan", "rowspan", "class"},
    "tr": {"class"},
    "thead": {"class"},
    "tbody": {"class"},
}

_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def sanitize_html(html: str | None) -> Markup:
    """Clean untrusted HTML and mark safe for Jinja (already-escaped)."""
    cleaned = nh3.clean(
        html or "",
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer nofollow",
    )
    return Markup(cleaned)


def enhance_tables(html: str | None) -> str:
    """Make author-written tables responsive + accessible before sanitizing.

    - Adds ``scope="col"`` to ``<th>`` without an explicit scope (screen readers).
    - Wraps each ``<table>`` in a horizontally-scrollable region so wide data
      tables never break mobile layout. The wrapper div/class survive
      :func:`sanitize_html` (div+class are allowlisted).
    """
    import re as _re

    text = html or ""

    def _scope_th(m: _re.Match) -> str:
        tag = m.group(0)
        if "scope" in tag.lower():
            return tag
        if tag.endswith("/>"):
            return tag[:-2] + ' scope="col"/>'
        return tag[:-1] + ' scope="col">'

    text = _re.sub(r"<th(\s[^>]*)?>", _scope_th, text, flags=_re.IGNORECASE)
    text = _re.sub(
        r"<table(\s[^>]*)?>",
        r'<div class="table-scroll" role="region" aria-label="Data table" tabindex="0"><table\1>',
        text,
        flags=_re.IGNORECASE,
    )
    text = _re.sub(r"</table>", "</table></div>", text, flags=_re.IGNORECASE)
    return text
