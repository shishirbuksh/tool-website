#!/usr/bin/env bash
# ============================================================
# CloudPanel Setup for StoryBrain AI
# Run AFTER app is running on port 8090.
#
# Usage:
#   ssh user@hostinger-vps
#   cd /opt/storybrain-ai
#   bash run.sh                              # First: install & start app
#   bash scripts/cloudpanel_proxy_setup.sh yourdomain.com  # Then: configure proxy
# ============================================================
set -euo pipefail

DOMAIN="${1:-}"
APP_PORT="${PORT:-8090}"

if [ -z "$DOMAIN" ]; then
    echo ""
    echo "Usage: bash scripts/cloudpanel_proxy_setup.sh yourdomain.com"
    echo ""
    echo "Sets up CloudPanel (NGINX) reverse proxy from your domain to localhost:$APP_PORT"
    exit 1
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   CloudPanel Setup — StoryBrain AI                      ║"
echo "║   Domain: $DOMAIN"
echo "║   Proxy : http://127.0.0.1:$APP_PORT"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ─── Vhost config template ───────────────────────────────────
VHOST_CONFIG=$(cat <<NGINX
server {
  listen 80;
  listen [::]:80;
  listen 443 ssl http2;
  listen [::]:443 ssl http2;
  {{ssl_certificate_key}}
  {{ssl_certificate}}
  server_name $DOMAIN;
  {{root}}

  {{nginx_access_log}}
  {{nginx_error_log}}

  if (\$scheme != "https") {
    rewrite ^ https://\$host\$uri permanent;
  }

  location ~ /.well-known {
    auth_basic off;
    allow all;
  }

  {{settings}}

  index index.html;

  location / {
    proxy_pass http://127.0.0.1:$APP_PORT/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-Server \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header Host \$http_host;
    proxy_pass_request_headers on;
    proxy_max_temp_file_size 0;
    proxy_connect_timeout 900;
    proxy_send_timeout 900;
    proxy_read_timeout 900;
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;
    proxy_busy_buffers_size 256k;
    proxy_temp_file_write_size 256k;
    proxy_redirect http://127.0.0.1:$APP_PORT/ https://$DOMAIN/;
  }

  location /static/ {
    alias /opt/storybrain-ai/static/;
    expires max;
    add_header Cache-Control "public, immutable";
    access_log on;
  }
}
NGINX
)

# ─── Method A: Reverse Proxy (recommended) ──────────────────
echo ""
log_info "=== Method A: Reverse Proxy (simplest, app stays at /opt/storybrain-ai) ==="
echo ""
log_info "CloudPanel Web UI:"
log_info "  1. Login at https://<your-server-ip>:8443"
log_info "  2. Sites → Add Site → Create Reverse Proxy"
log_info "  3. Domain: $DOMAIN"
log_info "  4. Forward URL: http://127.0.0.1:$APP_PORT"
log_info "  5. After creation: Sites → Manage → Vhost Editor"
log_info "  6. Replace everything with the config below"
log_info "  7. Sites → $DOMAIN → SSL/TLS → Issue Let's Encrypt"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Paste this in Vhost Editor (replaces all)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$VHOST_CONFIG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─── Method B: Python Site ──────────────────────────────────
echo ""
log_info "=== Method B: Python Site (CloudPanel manages everything) ==="
echo ""
log_info "This moves the app into CloudPanel's site structure."
log_info "Only use if you want CloudPanel to manage the app process too."
echo ""
log_info "Steps:"
log_info "  1. Create Python site via CLI or Web UI"
echo ""
if command -v clpctl >/dev/null 2>&1; then
    SITE_USER="${DOMAIN//./_}"
    SITE_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || echo "ChangeMe123!")
    echo "     clpctl site:add:python \\"
    echo "       --domainName=\"$DOMAIN\" \\"
    echo "       --pythonVersion=\"3.11\" \\"
    echo "       --appPort=\"$APP_PORT\" \\"
    echo "       --siteUser=\"$SITE_USER\" \\"
    echo "       --siteUserPassword=\"$SITE_PASS\""
    echo ""
    log_info "  2. Move app to CloudPanel directory:"
    echo "     sudo rsync -a /opt/storybrain-ai/ /home/$SITE_USER/htdocs/$DOMAIN/"
    echo "     sudo chown -R $SITE_USER:$SITE_USER /home/$SITE_USER/htdocs/$DOMAIN/"
    echo ""
    log_info "  3. Set up systemd service (see storybrain-ai.service)"
    log_info "  4. Enable SSL: Sites → $DOMAIN → SSL/TLS → Issue Let's Encrypt"
else
    log_info "  (clpctl not found — use Web UI: Sites → Add Site → Create Python Site)"
    log_info "    Domain: $DOMAIN, Python Version: 3.11, App Port: $APP_PORT"
fi

# ─── Final instructions ────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  After setup:                                           ║"
echo "║                                                          ║"
echo "║  1. Verify app is running:                               ║"
echo "║     curl http://127.0.0.1:$APP_PORT/healthz              ║"
echo "║                                                          ║"
echo "║  2. Visit https://$DOMAIN in browser            ║"
echo "║                                                          ║"
echo "║  3. App logs:                                            ║"
echo "║     journalctl -u storybrain-ai -n 50 --no-pager         ║"
echo "║                                                          ║"
echo "║  4. NGINX reload if needed:                              ║"
echo "║     sudo systemctl reload cloudpanel-nginx               ║"
echo "╚══════════════════════════════════════════════════════════╝"
