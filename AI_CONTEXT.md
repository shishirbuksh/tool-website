# StoryBrainAI Project Context

## Tech Stack
- Django 5.x+ (latest, Python 3.11+)
- HTML5 (Semantic, Accessible, Mobile-First)
- Tailwind CSS v4 (@tailwindcss/postcss, @theme)
- DaisyUI v5 (@plugin "daisyui")
- JavaScript (Vanilla, client-side execution for 122/128 tools)
- Caddy (reverse proxy, automatic HTTPS, Brotli/Gzip) + Gunicorn WSGI/ASGI on port 8090

## Catalog
- 128 free online tools (slugs defined in `data/tools.yaml`)
- 99 in-depth SEO guides across 6 topical pillars (`data/blog.yaml`)
- English-only architecture (canonical English URLs at root/tool/blog; legacy `/hi/`, `/es/`, `/fr/`, `/de/` paths issue HTTP 301 redirects to canonical English URLs)

## Project Structure
- `config/` → Django project core (`settings/`, `urls.py`, `wsgi.py`, `asgi.py`)
- `apps/catalog/` → Tools catalog, hubs, tool detail views
- `apps/blog/` → Blog articles, pillars, guides
- `apps/seo/` → Dynamic XML sitemaps, robots.txt, llms.txt, IndexNow verification
- `apps/tools_api/` → Computation endpoints (rembg, fpdf2, crypto, CORS proxy)
- `apps/analytics/` → High-throughput SQLite batch analytics
- `apps/core/` → Shared middleware, sanitize, icons, custom exceptions
- `templates/` → HTML templates (`templates/tools/<slug_with_underscores>.html`, `templates/blog/`, `templates/pages/`)
- `static/` → CSS, JS, images, fonts
- `data/` → `tools.yaml` (128 tools catalog) and `blog.yaml` (99 articles)
- `Caddyfile` → Reverse proxy configuration
- `deploy.sh` → VPS deployment engine
- `storybrain-ai.service` → Systemd unit file

## Design System (DataFast — DESIGN.md)
- Dark canvas: `#1A1A1A`
- Surface: `#252525`
- Surface-elevated: `#2E2E2E`
- Action (Coral): `#E86A4A`
- Action Hover: `#D55A3A`
- Ink: `#F5F5F5`
- Muted Ink: `#A0A0A0`
- Border: `#3A3A3A`
- Chart Line: `#7EC8E3`
- Chart Bar: `#E86A4A`
- Typography: `DM Sans` (Display & structural) + `Fuzzy Bubbles` (Handwritten annotations)
- Layout: Modern SaaS conversion pattern with centered hero, coral action button, URL search box, overlapping avatar social proof, and interactive browser preview chrome.

## UI/UX Standards
- Explicit button types: All `<button>` elements must specify `type="button"` (or `type="submit"` in forms).
- Search inputs: Use `type="search" inputmode="search" enterkeyhint="search" spellcheck="false"`.
- Focus & Touch states: All interactive elements declare `touch-action: manipulation`, `-webkit-tap-highlight-color: transparent`, and `:focus-visible` 2px contrast rings.
- Dialog scrolling: Overlays and modals must contain `overscroll-behavior: contain`.
- Typographic punctuation: Use typographic ellipsis `…` instead of literal triple dots `...`.
