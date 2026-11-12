# StoryBrainAI Project Context

## Tech Stack
- FastAPI
- Python 3.11+
- HTML
- Tailwind CSS
- JavaScript
- Caddy (reverse proxy, automatic HTTPS) + Gunicorn/Systemd on port 8090

## Catalog
- 126 free online tools (slugs defined in `data/tools.yaml`)
- English-only architecture (canonical English URLs at root/tool/blog; legacy `/hi/`, `/es/`, `/fr/`, `/de/` paths issue HTTP 301 redirects to canonical English URLs; shared audit JS `window.sbr.audit` wired into all 4 SEO tools: `keyword-data-analyzer`, `seo-writing-assistant`, `word-counter`, `page-grader`)

## Project Structure
- app/api → API routes
- templates/ → HTML templates (root-level; tool pages: templates/tools/<slug_with_underscores>.html)
- static/ → CSS, JS, images (root-level)
- app/core → Configuration
- app/services → Business logic
- data/tools.yaml → tool catalog (slugs, FAQs, related_slugs)
- Caddyfile → Caddy reverse proxy (CADDY_DOMAIN / CADDY_PROXY_UPSTREAM / CADDY_STATIC_ROOT)
- deploy.sh → VPS deploy engine (writes SECRET_KEY + APP_VERSION to .env)
- storybrain-ai.service → systemd unit (EnvironmentFile={{APP_DIR}}/.env, U2NET_HOME)

## Env / Caddy / Systemd
- Copy `.env.example` → `.env`; required: SECRET_KEY, APP_VERSION, ALLOWED_HOSTS,
  CORS_ORIGINS, CADDY_DOMAIN / CADDY_PROXY_UPSTREAM / CADDY_STATIC_ROOT
  (CADDY_STATIC_ROOT must equal $APP_DIR/static), FORWARDED_ALLOW_IPS=127.0.0.1,
  U2NET_HOME, HOST/PORT (defaults 0.0.0.0/8090).
- Caddy serves /static/* from CADDY_STATIC_ROOT and /sw.js with
  Service-Worker-Allowed: /; everything else reverse-proxies to 127.0.0.1:8090.

## Rules
- Mobile-first UI
- Accessible HTML
- SEO optimized
- Type hints
- Small reusable functions
- No duplicated code

## Before Changing Code
- Explain the plan
- List files to modify
- Wait for approval

## Design System (Apple × SAP)
- Synthesizes Apple's museum-gallery minimalism (SF Pro/Inter optical tracking, frosted glassmorphism `apple-glass`, pill action buttons `.apple-pill-btn`) with SAP's enterprise precision (Sapphire Blue `#0057d2`, structured 8px controls `.enterprise-control`, data tables `.sap-band`).
- Design contracts located in `DESIGN_APPLE.md`, `DESIGN_SAP.md`, and `DESIGN_SYNTHESIS.md`.

## Active Agent Skills (.agents/skills)
- FastAPI: `fastapi`, `fastapi-templates`, `fastapi-python`, `fastapi-code-review`
- SEO: `seo-audit`, `programmatic-seo`, `seo-competitor-pages`, `seo-content-writer`, `seo-technical`
- UI/UX & Web Design: `web-design-guidelines` (Vercel Web Interface Guidelines), `ui-ux-pro-max` (Design systems, micro-interactions, responsive accessibility, WCAG contrast)

## UI/UX Standards
- Explicit button types: All `<button>` elements must specify `type="button"` (or `type="submit"` in forms).
- Search inputs: Use `type="search" inputmode="search" enterkeyhint="search" spellcheck="false"`.
- Focus & Touch states: All interactive elements declare `touch-action: manipulation`, `-webkit-tap-highlight-color: transparent`, and `:focus-visible` 2px contrast rings.
- Dialog scrolling: Overlays and modals must contain `overscroll-behavior: contain`.
- Typographic punctuation: Use typographic ellipsis `…` instead of literal triple dots `...`.
