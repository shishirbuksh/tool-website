#!/usr/bin/env bash
# ============================================================
# CloudPanel Reverse Proxy Setup for StoryBrain AI
# Run AFTER app is running on port 8090.
#
# Usage:
#   ssh user@hostinger-vps
#   cd /opt/storybrain-ai
#   bash run.sh                              # First: install & start app
#   bash scripts/cloudpanel_proxy_setup.sh yourdomain.com  # Then: configure proxy
#
# Two methods (Method 1 is recommended):
#   1. Vhost Editor — paste config into CloudPanel web UI
#   2. CLI — uses clpctl to create reverse proxy site
# ============================================================
set -euo pipefail

DOMAIN="${1:-}"
APP_PORT="${PORT:-8090}"

if [ -z "$DOMAIN" ]; then
    echo ""
    echo "Usage: bash scripts/cloudpanel_proxy_setup.sh yourdomain.com"
    echo ""
    echo "This sets up a CloudPanel NGINX reverse proxy from your domain to localhost:$APP_PORT"
    echo ""
    echo "Two methods available:"
    echo "  1. CloudPanel Web UI (recommended) — copy the Vhost config below"
    echo "  2. CLI via clpctl — automated setup"
    exit 1
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ─── Vhost config template for CloudPanel ───────────────────
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

# ─── Method 1: Show Vhost config for Web UI ────────────────
echo ""
log_info "=== Method 1: CloudPanel Web UI (recommended) ==="
echo ""
log_info "1. Log into CloudPanel at https://<your-server-ip>:8443"
log_info "2. Go to Sites → Add Site → Create Reverse Proxy"
log_info "3. Set Domain: $DOMAIN, Forward URL: http://127.0.0.1:$APP_PORT"
log_info "4. After creation, go to Sites → Manage → Vhost Editor"
log_info "5. Replace the location / block with the enhanced config below"
log_info "6. Enable SSL: Sites → Manage → SSL/TLS → Issue Let's Encrypt"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "      Enhanced Vhost Config (paste in Vhost Editor)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "$VHOST_CONFIG"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ─── Method 2: Automatic via clpctl ───────────────────────
if command -v clpctl >/dev/null 2>&1; then
    echo ""
    log_info "=== Method 2: Automated CLI setup ==="
    echo ""
    log_warn "clpctl detected! Attempting automated reverse proxy setup..."

    SITE_USER="cloudpanel"
    SITE_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || echo "changethis123!")

    if sudo clpctl site:add:reverse-proxy \
        --domainName="$DOMAIN" \
        --reverseProxyUrl="http://127.0.0.1:$APP_PORT" \
        --siteUser="$SITE_USER" \
        --siteUserPassword="$SITE_PASS" 2>/dev/null; then

        log_info "Reverse proxy site created in CloudPanel."
        log_info "Now enable SSL in CloudPanel: Sites → $DOMAIN → SSL/TLS → Issue Let's Encrypt"
    else
        log_warn "clpctl command failed. Use Method 1 (Web UI) instead."
    fi
fi

# ─── Final instructions ────────────────────────────────────
echo ""
log_info "=== After setting up the reverse proxy ==="
echo ""
log_info "1. Make sure the app is running:  curl http://127.0.0.1:$APP_PORT/healthz"
log_info "2. Enable Let's Encrypt SSL in CloudPanel UI"
log_info "3. Visit https://$DOMAIN to verify"
log_info "4. To check NGINX config:  sudo nginx -t"
log_info "5. To reload NGINX:        sudo systemctl reload cloudpanel-nginx"
echo ""
log_info "App logs:   journalctl -u storybrain-ai -n 50 --no-pager"
log_info "NGINX logs: sudo tail -50 /var/log/nginx/${DOMAIN}.error.log"
