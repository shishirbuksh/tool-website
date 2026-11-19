"""Shared HTML sanitization — single source of truth for Jinja `sanitize` filter."""

from __future__ import annotations

import re
import nh3
from markupsafe import Markup
from django.conf import settings

_ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "dd", "div", "dl", "dt",
    "em", "h1", "h2", "h3", "h4", "hr", "i", "img", "li", "ol", "p", "pre", "span",
    "strong", "table", "tbody", "td", "th", "thead", "tr", "u", "ul",
}

_ALLOWED_ATTRIBUTES = {
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
    """Clean untrusted HTML and mark safe for Jinja."""
    cleaned = nh3.clean(
        html or "",
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer nofollow",
    )
    origin = getattr(settings, "SITE_URL", "https://www.storybrainai.com").rstrip("/")

    def _fix_link(m: re.Match) -> str:
        tag = m.group(0)
        href = m.group(1)
        if href.startswith(("/", "#")) or (origin and href.startswith(origin)):
            def _strip_nofollow(rm: re.Match) -> str:
                tokens = [t for t in rm.group(1).split() if t != "nofollow"]
                return 'rel="' + " ".join(tokens) + '"'

            tag = re.sub(r'rel="([^"]*)"', _strip_nofollow, tag)
        return tag

    cleaned = re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>', _fix_link, cleaned)
    return Markup(cleaned)


def enhance_tables(html: str | None) -> str:
    """Make author-written tables responsive + accessible before sanitizing."""
    text = html or ""

    def _scope_th(m: re.Match) -> str:
        tag = m.group(0)
        if "scope" in tag.lower():
            return tag
        if tag.endswith("/>"):
            return tag[:-2] + ' scope="col"/>'
        return tag[:-1] + ' scope="col">'

    text = re.sub(r"<th(\s[^>]*)?>", _scope_th, text, flags=re.IGNORECASE)
    text = re.sub(
        r"<table(\s[^>]*)?>",
        r'<div class="table-scroll" role="region" aria-label="Data table" tabindex="0"><table\1>',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"</table>", "</table></div>", text, flags=re.IGNORECASE)
    return text
