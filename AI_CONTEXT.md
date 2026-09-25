# StoryBrainAI Project Context

## Tech Stack
- FastAPI
- Python 3.11+
- HTML
- Tailwind CSS
- JavaScript
- Caddy (reverse proxy, automatic HTTPS) + Gunicorn/Systemd on port 8090

## Catalog
- 107 free online tools (slugs defined in `data/tools.yaml`)

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
