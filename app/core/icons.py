import json
import os
import re

_cache = {}

JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lucide_icons.json")
with open(JSON_PATH, encoding="utf-8") as f:
    _icons = json.load(f)

def lucide_icon(name: str, class_name: str = "", size: int = 24) -> str:
    cache_key = f"{name}_{size}"
    if cache_key in _cache:
        svg = _cache[cache_key]
    else:
        if name not in _icons:
            return f'<span class="icon-missing" title="Icon {name} not found"></span>'
        svg = _icons[name]
        _cache[cache_key] = svg

    # Inject class, size, and aria-hidden; preserve essential SVG attributes
    has_color_class = bool(re.search(r'\btext-(?:primary|secondary|accent|base-content|success|warning|error|info|neutral)\b', class_name))
    base_color = '' if has_color_class else 'color:var(--color-base-content);'

    def _replace_svg(m):
        original = m.group(1)
        keep = []
        for attr in ['xmlns', 'viewBox', 'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin']:
            found = re.search(rf'{re.escape(attr)}="[^"]*"', original)
            if found:
                keep.append(found.group(0))
        kept = ' '.join(keep)
        return f'<svg class="{class_name}" width="{size}" height="{size}" {kept} style="display:inline-block;{base_color}" aria-hidden="true" focusable="false">'

    svg = re.sub(r'<svg ([^>]*)>', _replace_svg, svg, count=1)
    return svg
