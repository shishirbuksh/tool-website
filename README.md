# StoryBrain AI

[![Visit StoryBrain AI](https://img.shields.io/badge/Visit-StoryBrain_AI-blue?style=for-the-badge)](https://www.storybrainai.com/)

![StoryBrain AI Banner](static/og-image.jpg)

**[StoryBrain AI](https://www.storybrainai.com/)** is a production-grade, lightning-fast SaaS platform offering 117 free browser-based tools. It includes AI utilities, crypto calculators, image processors, PDF generators, and business calculators.

The platform is engineered for absolute maximum performance (100/100 Core Web Vitals) featuring an enterprise architecture built on FastAPI, Jinja2, and TailwindCSS.

## 🚀 Enterprise Performance Architecture
- **Speculation Rules API:** Zero-millisecond (0ms) predictive prerendering on hover.
- **Zero-Byte CSS:** Tailwind `app.css` is strictly cached and version-busted on the backend for minimal TTFB.
- **Hydration-Free Frontend:** No heavy JS frameworks (React/Vue/Angular). Vanilla JS ensures zero main-thread blocking.
- **Lazy Loading:** Analytics and ads are debounced to guarantee 100/100 Lighthouse performance.

## 🛠️ Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** (High-performance API routing and middleware)
- **Jinja2** (Server-side HTML rendering)
- **Uvicorn & Gunicorn** (ASGI server and process manager)
- **SQLite** (Analytics tracking and storage)

### Frontend
- **HTML5 & Vanilla JavaScript**
- **TailwindCSS v4**
- **DaisyUI v5**

### Infrastructure
- **Hostinger VPS** (Ubuntu OS)
- **Caddy** (reverse proxy with automatic HTTPS — see `Caddyfile`)
- **Systemd** (`storybrain-ai.service` runs Gunicorn on port 8090)
- **Cloudflare** (CDN, Brotli Compression, HTTP/3 QUIC)

---

## 💻 Local Development

### Prerequisites
- Python 3.11+
- Node.js (for TailwindCSS building)
- GNU Make (optional, for automation)

### Quick Start
1. **Clone the repository:**
   ```bash
   git clone https://github.com/shishirbuksh/tool-website.git
   cd tool-website
   ```

2. **Run the Make command:**
   ```bash
   make run
   ```
   *This automatically installs dependencies, builds frontend assets, and starts the server.*

### Manual Start (Windows/No Make)
1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Install Node dependencies & build CSS:**
   ```bash
   npm ci
   npm run build
   ```
3. **Start the FastAPI server:**
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --reload
   ```

---

## 🧪 Testing
The project includes a 310+ test suite managed by `pytest`. Localized pages are covered by `tests/test_locale_policy.py`, `tests/test_locale_quarantine.py`, and `tests/test_quality_gate.py`; per-locale content guards live in `tests/test_i18n.py::TestLocaleContentQuality`.

```bash
# Run all tests
make test

# Or manually:
python -m pytest tests/ -v
```

> **Note:** The test suite generates an isolated SQLite database (`test_analytics.db`) in your system's temp directory to prevent any destructive mutations to production data.

---

## 🚢 Production Deployment

StoryBrain AI uses a seamless deployment script optimized for Hostinger VPS (Ubuntu).

1. SSH into your VPS.
2. Navigate to the repository directory.
3. Run the automated deployment pipeline:
   ```bash
   sudo bash deploy.sh
   ```

This script will automatically pull the latest `main` branch, rebuild assets, restart the Gunicorn workers via Systemd, and flush any necessary caches.

### IndexNow instant indexing (Bing/Yandex)
1. Generate a key: `python3 -c "import secrets; print(secrets.token_hex(16))"`
2. Set `INDEXNOW_KEY=<key>` in `.env` and deploy — the app serves `/<KEY>.txt` automatically.
3. Submit changed URLs after content passes: `python3 scripts/submit_indexnow.py --key <KEY> --url https://www.storybrainai.com/tool/calculator` (repeat `--url`, or `--url-file urls.txt`, or `--all` for the full sitemap with `--dry-run` to preview).
4. Multilingual: `--all-locales` submits only locales released in `data/locale_publication.yaml`; quarantined locale sitemaps and explicit URLs under those locales are skipped.

### Multilingual (HI/ES/FR/DE via subdirectories)
- **Release policy:** `data/locale_publication.yaml` is the source of truth. Every non-English locale is quarantined by default. A localized URL is indexable only when the locale is `published` **and** the item's `i18n.<locale>.translation_status` is `published`. Surface pages are released per surface (`home`, `tools`, `blog`, `blog_pillars`, `hubs`, `static`), and static/legal pages additionally need their path in `static_pages`. Everything else returns 200 with `noindex, follow`, self-canonical, no hreflang, and is omitted from sitemaps, `robots.txt` and IndexNow.
- **URLs:** English stays prefix-less (`/tool/emi-calculator`); Hindi/Spanish/French/German live under `/hi/`, `/es/`, `/fr/`, `/de/` with identical English slugs (no 301 equity loss). Released pages emit only their indexable hreflang cluster (`en` + released locales + `x-default`), per-locale canonical/OG (`hi_IN/es_ES/fr_FR/de_DE`) and `Content-Language` + `Vary: Accept-Language`.
- **Content:** `data/tools.yaml` / `data/blog.yaml` carry per-locale `i18n` overrides. The existing overrides are legacy machine drafts and stay quarantined until rebuilt as native content packs with `translation_status`, `reviewer`, `reviewed_at`, `author` and `sources`. Wave 1a (10 DE/ES items) is rebuilt and applied via `scripts/apply_content_pack.py`; audit a pack with `python scripts/quality_gate.py --pack data/content_packs/de_wave1a.yaml`. Run `python scripts/quality_gate.py --locale de --slug <slug>` for a single item. `python scripts/locale_backlog.py` reports every override's status, blockers and readiness; the DE/ES scope, applied state and UI blockers live in `MULTILINGUAL_BATCH_1.md` and `data/keyword_research_de_es_batch1.csv`. DE/ES calculator chrome is localized and protected by `tests/test_localized_calculator_ui.py`; the `/de/tools` and `/es/tools` directory chrome is still English, so the first DE/ES release keeps `surfaces: []` and leaves the directory noindex until its chrome is localized. The wave-1a blog item also stays `translation_status: review` until `templates/blog/post.html` / `blog_macros.html` are localized and the India-only SIP/FD links are filtered; the first release is 8 tool URLs.
- **Sitemaps:** `/sitemap.xml` + `/sitemap-index.xml` are live. Locale sitemaps are added only after release; while quarantined, `/sitemap-de.xml` returns 404 and the locale is absent from sitemap index, `robots.txt` and EN hreflang. No Caddy change needed (same upstream; subdirectories, not subdomains).
- **UI/search:** navbar globe switcher + mobile drawer language links (driven by `locale_urls`); `/api/tools/catalog?lang=hi|es|fr|de` returns translated names/URLs for the search dialog (`app.js` sends `document.documentElement.lang`).
- **Rollout:** DE + ES first, then FR, then HI. See `MULTILINGUAL_RUNBOOK.md` for the native-review, quality-gate, release and rollback procedure.

### Environment, Caddy & Systemd
- **Layout:** HTML templates live in `templates/` and static assets in `static/` (both at the repo root — not under `app/`). Tool pages are `templates/tools/<slug_with_underscores>.html` for each slug in `data/tools.yaml`.
- **Env:** copy `.env.example` to `.env` and set `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, plus `CADDY_DOMAIN` / `CADDY_PROXY_UPSTREAM` / `CADDY_STATIC_ROOT` (must equal `$APP_DIR/static`), `FORWARDED_ALLOW_IPS=127.0.0.1`, and `U2NET_HOME`. `deploy.sh` auto-generates `SECRET_KEY` if missing and persists `APP_VERSION` to `.env`.
- **Caddy:** `Caddyfile` reverse-proxies to Gunicorn on `127.0.0.1:8090`, serves `/static/*` from `CADDY_STATIC_ROOT`, and serves `/sw.js` with `Service-Worker-Allowed: /`. Override the apex domain with `CADDY_DOMAIN`.
- **Systemd:** `storybrain-ai.service` loads `{{APP_DIR}}/.env` via `EnvironmentFile`, runs `gunicorn app.main:app -c gunicorn_conf.py` as the `storybrainai` user, and sets `U2NET_HOME={{APP_DIR}}/.u2net`.

---

## 📄 License
Copyright (c) 2026 StoryBrain AI. All rights reserved.
