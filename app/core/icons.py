"""Lucide SVG icon rendering: lazy-loaded JSON, cache, and Jinja2 helper."""

import json
import os
import re

_cache = {}

_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lucide_icons.json")
_icons = None

_ATTRS_TO_KEEP = {"xmlns", "viewBox", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"}


def _load_icons():
    global _icons
    if _icons is None:
        with open(_JSON_PATH, encoding="utf-8") as f:
            _icons = json.load(f)


def lucide_icon(name: str, class_name: str = "", size: int = 24) -> str:
    _load_icons()

    cache_key = f"{name}_{size}"
    if cache_key in _cache:
        svg = _cache[cache_key]
    else:
        if name not in _icons:
            return f'<span class="icon-missing" title="Icon {name} not found"></span>'
        svg = _icons[name]
        _cache[cache_key] = svg

    has_color_class = bool(
        re.search(r"\btext-(?:primary|secondary|accent|base-content|success|warning|error|info|neutral)\b", class_name)
    )
    base_color = "" if has_color_class else "color:var(--color-base-content);"

    start = svg.index("<svg ")
    end = svg.index(">", start) + 1
    tag = svg[start:end]

    kept = []
    for attr in _ATTRS_TO_KEEP:
        pattern = rf'{re.escape(attr)}="[^"]*"'
        found = re.search(pattern, tag)
        if found:
            kept.append(found.group(0))

    new_tag = f'<svg class="{class_name}" width="{size}" height="{size}" {" ".join(kept)} style="display:inline-block;{base_color}" aria-hidden="true" focusable="false">'
    svg = new_tag + svg[end:]
    return svg
