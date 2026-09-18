"""Lucide SVG icon rendering: lazy-loaded JSON, cache, and Jinja2 helper."""

import html
import json
import os
import re
import threading
from collections import OrderedDict

_cache: OrderedDict[str, str] = OrderedDict()
_cache_lock = threading.Lock()
_icons_lock = threading.Lock()
_MAX_CACHE_SIZE = 500

_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lucide_icons.json")
_icons = None

# Ordered list (not a set) so kept attributes render deterministically.
_ATTRS_TO_KEEP = ["xmlns", "viewBox", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"]

_COLOR_CLASS_RE = re.compile(
    r"\btext-(?:primary|secondary|accent|base-content|success|warning|error|info|neutral)\b"
)


def _load_icons():
    global _icons
    if _icons is None:
        with _icons_lock:
            if _icons is None:
                with open(_JSON_PATH, encoding="utf-8") as f:
                    _icons = json.load(f)


def lucide_icon(name: str, class_name: str = "", size: int = 24) -> str:
    _load_icons()

    try:
        size_int = int(size)
    except (TypeError, ValueError):
        size_int = 24
    size_int = max(1, min(size_int, 512))
    safe_class = html.escape(class_name, quote=True)
    safe_name = html.escape(name, quote=True)

    # Cache raw SVG by name only (size/class applied per-call).
    with _cache_lock:
        svg = _cache.get(name)
        if svg is not None:
            _cache.move_to_end(name)
        else:
            if name not in _icons:
                return f'<span class="icon-missing" title="Icon {safe_name} not found"></span>'
            svg = _icons[name]
            _cache[name] = svg
            if len(_cache) > _MAX_CACHE_SIZE:
                _cache.popitem(last=False)

    has_color_class = bool(_COLOR_CLASS_RE.search(class_name))
    base_color = "" if has_color_class else "color:var(--color-base-content);"

    try:
        start = svg.index("<svg")
        end = svg.index(">", start) + 1
    except ValueError:
        return f'<span class="icon-missing" title="Malformed icon {safe_name}"></span>'
    tag = svg[start:end]

    kept = []
    for attr in _ATTRS_TO_KEEP:
        found = re.search(rf'{re.escape(attr)}="[^"]*"', tag)
        if found:
            kept.append(found.group(0))

    new_tag = f'<svg class="{safe_class}" width="{size_int}" height="{size_int}" {" ".join(kept)} style="display:inline-block;{base_color}" aria-hidden="true" focusable="false">'
    inner = svg[end:]
    if "</svg>" not in inner:
        return f'<span class="icon-missing" title="Malformed icon {safe_name} (no closing tag)"></span>'
    svg = new_tag + inner
    return svg
