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
    """Clean untrusted HTML and mark safe for Jinja (already-escaped).

    nh3 applies ``link_rel`` to every anchor, so post-process: strip the
    ``nofollow`` token from same-origin links (``/path``, ``#frag``) to keep
    internal equity flowing, while external links keep full nofollow.
    """
    cleaned = nh3.clean(
        html or "",
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer nofollow",
    )
    try:
        from app.core.config import settings as _settings  # noqa: PLC0415

        _origin = (_settings.SITE_URL or "").rstrip("/")
    except Exception:
        _origin = "https://www.storybrainai.com"
    import re as _re

    def _fix_link(m: _re.Match) -> str:
        tag = m.group(0)
        href = m.group(1)
        if href.startswith(("/", "#")) or (_origin and href.startswith(_origin)):

            def _strip_nofollow(rm: _re.Match) -> str:
                tokens = [t for t in rm.group(1).split() if t != "nofollow"]
                return 'rel="' + " ".join(tokens) + '"'

            tag = _re.sub(r'rel="([^"]*)"', _strip_nofollow, tag)
        return tag

    cleaned = _re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>', _fix_link, cleaned)
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
