import os
import re
import json

_cache = {}

JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lucide_icons.json")
with open(JSON_PATH, "r", encoding="utf-8") as f:
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

    # Inject class, size, and aria-hidden (remove original class/width/height from source)
    svg = re.sub(
        r'<svg ([^>]*)>',
        lambda m: f'<svg class="{class_name}" width="{size}" height="{size}" style="display:inline-block" aria-hidden="true" focusable="false">',
        svg,
        count=1,
    )
    return svg
