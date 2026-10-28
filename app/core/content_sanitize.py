"""Clean legacy localization artifacts before rendering.

The first machine-translation pass leaked prompt scaffolding into localized
copy (``<p>LSI: precision, speed, privacy.</p>``). Those strings are not user
content and must never be rendered or indexed. This module removes the
scaffolding without touching the English source or rewriting legitimate prose.
"""

from __future__ import annotations

import re
from typing import Any

_LSI_BLOCK_RE = re.compile(r"<p[^>]*>\s*LSI\s*:.*?</p>", re.IGNORECASE | re.DOTALL)
_LSI_INLINE_RE = re.compile(r"\bLSI\s*:\s*[^.<\n]*(?:[.<]|$)", re.IGNORECASE)


def clean_localized_text(value: str) -> str:
    """Strip ``LSI:`` scaffolds from one localized string."""
    if not value or "LSI" not in value.upper():
        return value
    cleaned = _LSI_BLOCK_RE.sub("", value)
    cleaned = _LSI_INLINE_RE.sub("", cleaned)
    return cleaned.strip()


def clean_localized_value(value: Any) -> Any:
    """Recursively clean strings in a localized override structure."""
    if isinstance(value, str):
        return clean_localized_text(value)
    if isinstance(value, list):
        return [clean_localized_value(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_localized_value(item) for key, item in value.items()}
    return value
