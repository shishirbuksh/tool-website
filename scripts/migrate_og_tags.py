"""Replace tool template {% block og_tags %}...{% endblock %} with individual
{% block og_title %}, {% block og_description %} overrides."""
import os
import re
from pathlib import Path

td = Path(__file__).resolve().parent.parent / "templates" / "tools"

# Pattern to capture the full og_tags block and extract title/desc
BLOCK_RE = re.compile(
    r"{% block og_tags %}\s*\n"
    r"(.*?)"
    r"{% endblock %}\s*\n?",
    re.DOTALL,
)

# Extract og:title value
TITLE_RE = re.compile(r'meta property="og:title"\s+content="([^"]+)"')
# Extract og:description value
DESC_RE = re.compile(r'meta property="og:description"\s+content="([^"]+)"')
# Check if og:image exists
IMAGE_RE = re.compile(r'meta property="og:image"')

count = 0
for fpath in sorted(td.glob("*.html")):
    text = fpath.read_text(encoding="utf-8")
    m = BLOCK_RE.search(text)
    if not m:
        continue

    block_text = m.group(1)
    title_m = TITLE_RE.search(block_text)
    desc_m = DESC_RE.search(block_text)
    has_image = bool(IMAGE_RE.search(block_text))

    if not title_m or not desc_m:
        print(f"  SKIP {fpath.name}: missing title/desc in og_tags block")
        continue

    og_title = title_m.group(1)
    og_desc = desc_m.group(1)

    # Build replacement blocks
    new_blocks = f"{{% block og_title %}}{og_title}{{% endblock %}}\n"
    new_blocks += f"{{% block og_description %}}{og_desc}{{% endblock %}}\n"

    # If template had no og:image, it must have wanted to suppress it
    if not has_image:
        new_blocks += "{% block og_image %}{% endblock %}\n"

    # Replace the whole og_tags block
    new_text = BLOCK_RE.sub(new_blocks, text, count=1)
    if new_text != text:
        fpath.write_text(new_text, encoding="utf-8")
        print(f"  UPDATED {fpath.name}: title={og_title[:50]}...")
        count += 1

print(f"\nUpdated {count} templates")
