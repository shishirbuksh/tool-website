# StoryBrain AI

[![Visit StoryBrain AI](https://img.shields.io/badge/Visit-StoryBrain_AI-blue?style=for-the-badge)](https://www.storybrainai.com/)

![StoryBrain AI Banner](static/og-image.jpg)

**[StoryBrain AI](https://www.storybrainai.com/)** is a production-grade, lightning-fast SaaS platform offering 126 free browser-based tools. It includes AI utilities, crypto calculators, image processors, PDF generators, and business calculators.

The platform is engineered for absolute maximum performance (100/100 Core Web Vitals) featuring an enterprise full-stack architecture built on modern Django, Jinja2, DaisyUI v5, and TailwindCSS v4 with DataFast conversion-focused UI design.

## 🚀 Enterprise Performance Architecture
- **Speculation Rules API:** Zero-millisecond (0ms) predictive prerendering on hover.
- **DataFast SaaS Conversion UI:** Dark-first `#1A1A1A` high-contrast aesthetic with Action Coral `#E86A4A` accents.
- **Zero-Byte CSS:** Tailwind `app.css` is strictly cached and version-busted on the backend for minimal TTFB.
- **Hydration-Free Frontend:** No heavy JS frameworks (React/Vue/Angular). Vanilla JS ensures zero main-thread blocking.
- **Lazy Loading:** Analytics and ads are debounced to guarantee 100/100 Lighthouse performance.

## 🛠️ Tech Stack

### Backend
- **Python 3.11+ / 3.14**
- **Django 6** (Modern decoupled domain architecture: `apps.core`, `apps.catalog`, `apps.blog`, `apps.seo`, `apps.tools_api`, `apps.analytics`)
- **Jinja2 & Django Templates** (Server-side HTML rendering)
- **Gunicorn** (WSGI server with gthread workers)
- **SQLite / Redis** (Analytics tracking and high-throughput caching)

### Frontend
- **HTML5 & Vanilla JavaScript**
- **TailwindCSS v4**
- **DaisyUI v5**
- **DataFast Design System** (Dark surface layers, coral action buttons, accessible typography)

### Infrastructure
- **Hostinger VPS** (Ubuntu OS)
- **Caddy** (reverse proxy with automatic HTTPS — see `Caddyfile`)
- **Systemd** (`storybrain-ai.service` runs Gunicorn on port 8090)
- **Cloudflare** (CDN, Brotli Compression, HTTP/3 QUIC)

---

## 💻 Local Development

### Prerequisites
- Python 3.11+
- Node.js (for TailwindCSS & DaisyUI bundling)
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
3. **Start the Django development server:**
   ```bash
   python manage.py runserver 127.0.0.1:8090
   ```
   *Or for production WSGI test:*
   ```bash
   gunicorn -c gunicorn_conf.py config.wsgi:application
   ```

---

## 🧪 Testing
The project includes a test suite managed by `pytest` covering core routes, English SEO/canonical tags, legacy locale `301` redirects, content quality, and sitemap consistency (`scripts/quality_gate.py`).

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
3. Submit changed URLs after content passes: `python scripts/submit_indexnow.py --key <KEY> --url https://www.storybrainai.com/tool/emi-calculator` (repeat `--url`, or `--url-file urls.txt`, or `--all` for the full `/sitemap.xml` with `--dry-run` to preview).

### English-Only Canonical URLs & Legacy Redirects
- **Canonical URLs:** All tools, hubs, guides, and static pages live cleanly at English paths (`/tool/<slug>`, `/blog/<pillar>/<slug>`, `/calculators`, `/student-tools`, etc.).
- **Legacy locale redirects:** Legacy `/hi/*`, `/es/*`, `/fr/*`, and `/de/*` URLs issue HTTP `301` permanent redirects to their canonical English URLs; `/sitemap-index.xml` and `/sitemap-en.xml` `301`-redirect to `/sitemap.xml`, and `/sitemap-{hi,es,fr,de}.xml` return `404`.

### Environment, Caddy & Systemd
- **Layout:** HTML templates live in `templates/` and static assets in `static/` (both at the repo root — not under `app/`). Tool pages are `templates/tools/<slug_with_underscores>.html` for each slug in `data/tools.yaml`.
- **Env:** copy `.env.example` to `.env` and set `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, plus `CADDY_DOMAIN` / `CADDY_PROXY_UPSTREAM` / `CADDY_STATIC_ROOT` (must equal `$APP_DIR/static`), `FORWARDED_ALLOW_IPS=127.0.0.1`, and `U2NET_HOME`. `deploy.sh` auto-generates `SECRET_KEY` if missing and persists `APP_VERSION` to `.env`.
- **Caddy:** `Caddyfile` reverse-proxies to Gunicorn on `127.0.0.1:8090`, serves `/static/*` from `CADDY_STATIC_ROOT`, and serves `/sw.js` with `Service-Worker-Allowed: /`. Override the apex domain with `CADDY_DOMAIN`.
- **Systemd:** `storybrain-ai.service` loads `{{APP_DIR}}/.env` via `EnvironmentFile`, runs `gunicorn app.main:app -c gunicorn_conf.py` as the `storybrainai` user, and sets `U2NET_HOME={{APP_DIR}}/.u2net`.

---

## 📄 License
Copyright (c) 2026 StoryBrain AI. All rights reserved.
