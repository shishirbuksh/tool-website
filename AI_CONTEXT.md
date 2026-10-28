# StoryBrainAI Project Context

## Tech Stack
- FastAPI
- Python 3.11+
- HTML
- Tailwind CSS
- JavaScript
- Caddy (reverse proxy, automatic HTTPS) + Gunicorn/Systemd on port 8090

## Catalog
- 117 free online tools (slugs defined in `data/tools.yaml`)
- i18n: HI/ES/FR/DE via subdirectories (`/hi/ /es/ /fr/ /de/`, English slugs kept); per-locale `i18n:` overrides in `data/tools.yaml` / `data/blog.yaml`. Locale publication is two-gate (`data/locale_publication.yaml` + per-item `translation_status: published`), with per-surface release and a `static_pages` path allowlist; every non-EN locale is quarantined by default (200 `noindex, follow`, no hreflang, absent from sitemaps/robots/IndexNow). Existing overrides are legacy machine drafts: rebuild with native review and `scripts/quality_gate.py` before releasing (see `MULTILINGUAL_RUNBOOK.md`); 10 DE/ES wave-1a overrides are rebuilt and applied via `scripts/apply_content_pack.py`, and `quality_gate.py --pack` audits exactly a pack's slugs; they remain blocked on native reviewer/date; DE/ES calculator chrome is localized (native affordability template, EUR defaults, locale-aware formatter) and covered by `tests/test_localized_calculator_ui.py`, while `/de/tools` + `/es/tools` directory chrome remains English, so the first release keeps `surfaces: []` and adds `tools`/`blog` only after their hub chrome is localized; the wave-1a blog item stays `translation_status: review` until post chrome is localized and its India-only SIP/FD links are filtered, so the first release is 8 tool URLs. `scripts/locale_backlog.py` reports all 864 overrides with blockers/readiness, and `MULTILINGUAL_BATCH_1.md` + `data/keyword_research_de_es_batch1.csv` hold the DE/ES batch, applied state and keyword worksheet; helpers in `app/core/i18n.py` + `app/core/locale_policy.py`; locale routes in `pages.py`/`blog.py`/`seo.py`; sitemaps `/sitemap.xml + -index.xml` plus `-hi/-es/-fr/-de.xml` only for released locales; shared audit JS `window.sbr.audit` (density 0.5-2.5%, LSI + long-tail, thesaurus-backed) wired into all 4 SEO tools (`keyword-data-analyzer`, `seo-writing-assistant`, `word-counter`, `page-grader`)

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
