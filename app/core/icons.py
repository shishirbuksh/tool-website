import os
import re

_cache = {}

LUCIDE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "node_modules", "lucide-static", "icons")

# Strip license comment, collapse whitespace, remove SVG attrs that we override
_RE_COMMENT = re.compile(r'<!--.*?-->')
_RE_NEWLINES = re.compile(r'>\s+<')
_RE_WHITESPACE = re.compile(r'\s{2,}')

def lucide_icon(name: str, class_name: str = "", size: int = 24) -> str:
    cache_key = f"{name}_{size}"
    if cache_key in _cache:
        svg = _cache[cache_key]
    else:
        filepath = os.path.join(LUCIDE_PATH, f"{name}.svg")
        try:
            if not os.path.exists(filepath):
                return f'<span class="icon-missing" title="Icon {name} not found"></span>'
            with open(filepath, encoding="utf-8") as f:
                svg = f.read()
            # Strip license comment, collapse to single line
            svg = _RE_COMMENT.sub("", svg)
            svg = _RE_NEWLINES.sub("><", svg)
            svg = _RE_WHITESPACE.sub(" ", svg).strip()
            _cache[cache_key] = svg
        except OSError:
            return f'<span class="icon-missing" title="Icon {name} not found"></span>'

    # Inject class, size, and aria-hidden (remove original class/width/height from source)
    svg = re.sub(
        r'<svg ([^>]*)>',
        lambda m: f'<svg class="{class_name}" width="{size}" height="{size}" style="display:inline-block" aria-hidden="true" focusable="false">',
        svg,
        count=1,
    )
    return svg
