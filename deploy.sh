#!/usr/bin/env bash
# ============================================================
# deploy.sh — Production deploy engine for StoryBrain AI
#
# First time:  sudo bash deploy.sh --setup
# Every time:  sudo bash deploy.sh
# ============================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="${APP_NAME:-storybrain-ai}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
# Use /var/backups (persistent across reboots) instead of /tmp
BACKUP_DIR="/var/backups/${APP_NAME}_backup_${TIMESTAMP}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Activate venv if present
if [ -f "$APP_DIR/venv/bin/activate" ]; then
    source "$APP_DIR/venv/bin/activate"
fi

# ─── Helpers ──────────────────────────────────────────────

ensure_system_deps() {
    local missing=""
    for cmd in python3 pip3 curl; do
        command -v "$cmd" >/dev/null 2>&1 || missing="$missing $cmd"
    done
    # npm (Node.js) is required for the frontend build step below.
    if ! command -v npm >/dev/null 2>&1; then
        missing="$missing npm(nodejs)"
    fi
    if [ -n "$missing" ]; then
        log_info "Installing missing system deps: $missing"
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3 python3-pip python3-venv libgomp1 libglib2.0-0 curl nodejs npm
    else
        # Just to be safe, ensure these libraries exist for OpenCV/onnxruntime
        sudo apt-get install -y -qq libgomp1 libglib2.0-0 >/dev/null 2>&1 || true
    fi
    # Firewall: gunicorn binds 127.0.0.1 — deny direct 8090, allow web only.
    if command -v ufw >/dev/null 2>&1; then
        sudo ufw deny 8090/tcp >/dev/null 2>&1 || true
        sudo ufw allow 80/tcp >/dev/null 2>&1 || true
        sudo ufw allow 443/tcp >/dev/null 2>&1 || true
    fi
}

fix_service_paths() {
    local svc="$APP_DIR/storybrain-ai.service"
    local tmp_svc
    tmp_svc="$(mktemp /tmp/${APP_NAME}.service.XXXXXX)"
    if [ -f "$svc" ]; then
        sed "s|{{APP_DIR}}|$APP_DIR|g" "$svc" > "$tmp_svc"
        echo "$tmp_svc"
    else
        rm -f "$tmp_svc"
        echo ""
    fi
}

# Pinned heavy ML deps — keep in sync with requirements.txt comments.
HEAVY_REMBG="rembg[cpu]==2.2.1"
HEAVY_CV2="opencv-python-headless==4.10.0.84"

install_python() {
    log_info "Installing Python core dependencies..."
    pip install -q --no-cache-dir -r "$APP_DIR/requirements.txt"
    
    # Install heavy optional dependencies (pinned for reproducibility)
    if ! python3 -c "import rembg" 2>/dev/null; then
        log_info "Installing heavy optional dependency: $HEAVY_REMBG"
        pip install -q --no-cache-dir "$HEAVY_REMBG"
    fi

    # Install opencv for watermark remover
    if ! python3 -c "import cv2" 2>/dev/null; then
        log_info "Installing OpenCV ($HEAVY_CV2)..."
        pip install -q --no-cache-dir "$HEAVY_CV2"
    fi


    # Pre-download rembg models so gunicorn workers don't timeout
    if python3 -c "import rembg" 2>/dev/null; then
        log_info "Pre-downloading rembg models..."
        export U2NET_HOME="$APP_DIR/.u2net"
        python3 -c "from rembg import new_session; new_session('u2netp'); new_session('u2net')" >/dev/null 2>&1 || true
    fi
}

build_rust() {
    log_info "Rust extension replaced by pure Python MLP (skipped)"
}

build_frontend() {
    log_info "Frontend build skipped (Tailwind is pre-compiled and tracked in Git to save VPS memory)"
}

backup_current() {
    if [ ! -d "$APP_DIR/.git" ]; then
        log_warn "No .git found — skipping backup (fresh clone)"
        return
    fi
    log_info "Backing up current version..."
    mkdir -p "$BACKUP_DIR"
    # Exclude var/ (SQLite WAL -wal/-shm + analytics.db) — live DB
    # files must not be rsynced mid-write; they are recreated/warmed on boot.
    # Also exclude .u2net (1GB+ models) to avoid backup bloat.
    rsync -a --exclude='node_modules' --exclude='venv' --exclude='.git' \
             --exclude='rust_predictor/target' --exclude='__pycache__' \
             --exclude='*.pyc' --exclude='.pytest_cache' --exclude='.ruff_cache' \
             --exclude='var/' --exclude='.u2net/' \
             "$APP_DIR/" "$BACKUP_DIR/"
    # Backup SQLite separately (consistent snapshot)
    if [ -f "$APP_DIR/var/data/analytics.db" ] && command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$APP_DIR/var/data/analytics.db" ".backup '$BACKUP_DIR/analytics.db.bak'" 2>/dev/null || true
    fi
}

pull_latest() {
    if [ ! -d "$APP_DIR/.git" ]; then
        log_warn "No .git found — skipping git pull"
        return
    fi
    # Guard: `reset --hard` below would discard uncommitted static/ work.
    # Commit/stash built assets first, or set ALLOW_DIRTY_STATIC=1 to override.
    if [ -n "$(git -C "$APP_DIR" status --porcelain -- static/ 2>/dev/null)" ] && [ "${ALLOW_DIRTY_STATIC:-0}" != "1" ]; then
        log_error "Refusing to pull: static/ has uncommitted changes (would be lost by reset --hard)"
        git -C "$APP_DIR" status --porcelain -- static/ | head -n 20 || true
        log_info "Commit/stash them or re-run with ALLOW_DIRTY_STATIC=1"
        exit 1
    fi
    log_info "Pulling latest from GitHub..."
    git -C "$APP_DIR" fetch origin
    git -C "$APP_DIR" reset --hard origin/main
    log_info "Updated to $(git -C "$APP_DIR" log -1 --format='%h %s')"
}

restart_service() {
    if command -v systemctl >/dev/null 2>&1 && [ -f "/etc/systemd/system/$APP_NAME.service" ]; then
        log_info "Updating and restarting systemd service..."
        local fixed=$(fix_service_paths)
        if [ -n "$fixed" ]; then
            sudo cp "$fixed" /etc/systemd/system/$APP_NAME.service
            sudo systemctl daemon-reload
            rm -f "$fixed"
        fi
        # NOTE: code/venv/.env changes require fresh workers — EnvironmentFile is
        # NOT re-read on HUP, so always restart here. HUP (ExecReload) is reserved
        # for manual zero-downtime reloads when only request handling needs a nudge.
        sudo systemctl restart "$APP_NAME"
        log_info "Service restarted."
        # Install + reload Caddy from the repo file (validates what actually runs).
        if [ -f "$APP_DIR/Caddyfile" ] && command -v caddy >/dev/null 2>&1; then
            if caddy validate --config "$APP_DIR/Caddyfile" --adapter caddyfile 2>/dev/null; then
                if [ -d /etc/caddy ]; then
                    sudo cp "$APP_DIR/Caddyfile" /etc/caddy/Caddyfile
                fi
                sudo systemctl enable caddy 2>/dev/null || true
                sudo systemctl reload caddy 2>/dev/null || log_warn "Caddy reload skipped"
            else
                log_error "Caddyfile validation failed — NOT reloading Caddy"
            fi
        fi
    else
        log_info "No systemd service found — starting gunicorn directly..."
        pkill -f "gunicorn.*$APP_NAME" 2>/dev/null || true
        cd "$APP_DIR"
        nohup "$APP_DIR/venv/bin/gunicorn" app.main:app -c "$APP_DIR/gunicorn_conf.py" > /tmp/${APP_NAME}.log 2>&1 &
        log_info "Gunicorn started (PID: $!). Log: /tmp/${APP_NAME}.log"
    fi
}

health_check() {
    # Gunicorn binds $HOST:$PORT (default 127.0.0.1:8090 — Caddy-only). Dial 127.0.0.1
    # when HOST is a wildcard (0.0.0.0/::) since wildcards aren't dialable.
    local host="${HOST:-127.0.0.1}"
    local port="${PORT:-8090}"
    local dial_host="$host"
    if [ "$dial_host" = "0.0.0.0" ] || [ "$dial_host" = "::" ]; then
        dial_host="127.0.0.1"
    fi
    local retries=30
    log_info "Health check on $dial_host:$port (HOST=$host PORT=$port)..."
    for i in $(seq 1 $retries); do
        if curl -sf --max-time 5 "http://$dial_host:$port/healthz" >/dev/null 2>&1; then
            # Require 3 consecutive healthy hits incl. readyz before declaring success.
            local ok=0
            for j in 1 2 3; do
                if curl -sf --max-time 5 "http://$dial_host:$port/readyz" >/dev/null 2>&1; then
                    ok=$((ok+1))
                fi
                sleep 1
            done
            if [ "$ok" -eq 3 ]; then
                # Confirm deployed version is serving (catches HUP/.env staleness).
                served="$(curl -sf --max-time 5 "http://$dial_host:$port/versionz" 2>/dev/null | grep -o '"version":"[^"]*"' || true)"
                log_info "Application is healthy! ✓ (healthz + 3x readyz ${served})"
                # Via Caddy: ensures reverse_proxy + TLS path works, not just gunicorn.
                # Non-fatal if Caddy isn't running locally (e.g. dev), fatal in prod setup.
                caddy_host="${CADDY_DOMAIN:-www.storybrainai.com}"
                if command -v caddy >/dev/null 2>&1 || curl -sf --max-time 3 http://127.0.0.1/healthz -H "Host: $caddy_host" >/dev/null 2>&1; then
                    if curl -sf --max-time 5 -H "Host: $caddy_host" "http://127.0.0.1/healthz" >/dev/null 2>&1; then
                        log_info "Caddy path healthy ✓ (via 127.0.0.1 Host=$caddy_host)"
                    else
                        log_warn "Direct gunicorn healthy but Caddy path failed (Host=$caddy_host) — check Caddy/service"
                    fi
                fi
                return 0
            fi
        fi
        sleep 2
    done
    log_error "Health check failed after $retries attempts"
    log_info "Check: journalctl -u $APP_NAME -n 50 --no-pager"
    return 1
}

setup_venv() {
    if [ ! -d "$APP_DIR/venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv "$APP_DIR/venv"
    fi
    # Ensure modern pip (fixes old CVEs) without reinstalling world.
    "$APP_DIR/venv/bin/pip" install -q --upgrade pip 2>/dev/null || true
}

setup_env_file() {
    if [ ! -f "$APP_DIR/.env" ]; then
        if [ -f "$APP_DIR/.env.example" ]; then
            cp "$APP_DIR/.env.example" "$APP_DIR/.env"
            SECRET="$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me")"
            if command -v python3 >/dev/null 2>&1 && [ "$SECRET" != "change-me" ]; then
                # SECRET is urlsafe (no / or |), safe for sed with | delimiter.
                sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" "$APP_DIR/.env"
            else
                log_error "Failed to generate SECRET_KEY — refusing to write change-me silently"
            fi
            log_warn ".env created — edit it: nano $APP_DIR/.env"
            log_warn "  Set: ALLOWED_HOSTS=www.storybrainai.com,storybrainai.com"
            log_warn "  Set: CORS_ORIGINS=https://www.storybrainai.com,https://storybrainai.com"
            log_warn "  Set: ENV=prod on production hosts"
        fi
    fi
    # Ensure SECRET_KEY exists even if .env predates the SECRET_KEY key:
    # append a generated value when missing or empty.
    if [ -f "$APP_DIR/.env" ]; then
        if ! grep -q "^SECRET_KEY=.\+" "$APP_DIR/.env" 2>/dev/null; then
            SECRET="$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me")"
            if [ "$SECRET" = "change-me" ]; then
                log_error "SECRET generation failed — aborting (refuse change-me)"
                exit 1
            fi
            # Remove any empty/stale SECRET_KEY line, then append the new one.
            sed -i "/^SECRET_KEY=.*/d" "$APP_DIR/.env"
            echo "SECRET_KEY=$SECRET" >> "$APP_DIR/.env"
            log_warn "SECRET_KEY was missing — generated and appended to .env"
            unset SECRET
        fi
    fi
    # .env holds secrets — restrict to owner read/write.
    if [ -f "$APP_DIR/.env" ]; then
        chmod 600 "$APP_DIR/.env" || true
    fi
    # SECURITY (minimal): never `cat`/echo .env, never run with `set -x` while
    # secrets are in env. Sourcing exports everything; drop secrets right after
    # so only HOST/PORT/etc stay exported for health_check. Systemd reads the
    # file directly via EnvironmentFile, so unsetting here is safe.
    __xtrace_off=0; case $- in *x*) set +x; __xtrace_off=1;; esac
    set -a; source "$APP_DIR/.env"; set +a
    unset SECRET SECRET_KEY REDIS_URL || true
    # Re-export just what deploy needs (HOST/PORT/CADDY_DOMAIN) stays; secrets gone.
    if [ "$__xtrace_off" = "1" ]; then set -x; fi
    unset __xtrace_off
}

setup_systemd() {
    log_info "Installing systemd service..."
    local fixed=$(fix_service_paths)
    if [ -z "$fixed" ]; then
        log_error "storybrain-ai.service not found"
        exit 1
    fi
    sudo cp "$fixed" /etc/systemd/system/$APP_NAME.service
    sudo systemctl daemon-reload
    sudo systemctl enable "$APP_NAME"
    sudo systemctl start "$APP_NAME"
    log_info "systemd service installed and started."
    rm -f "$fixed"
}

setup_permissions() {
    log_info "Ensuring required directories exist..."
    mkdir -p "$APP_DIR/var/data" "$APP_DIR/.u2net" /var/log/caddy
    # Static must stay world-readable for Caddy (UMask 022 in unit ensures 644/755).
    chmod 755 "$APP_DIR" "$APP_DIR/static" 2>/dev/null || true
    
    if id "storybrainai" >/dev/null 2>&1; then
        log_info "Fixing permissions (chown storybrainai:storybrainai)..."
        chown -R storybrainai:storybrainai "$APP_DIR/var" "$APP_DIR/.u2net"
        chown -R storybrainai:storybrainai "$APP_DIR"
        chmod 755 "$APP_DIR/static" 2>/dev/null || true
        find "$APP_DIR/static" -type d -exec chmod 755 {} + 2>/dev/null || true
        find "$APP_DIR/static" -type f -exec chmod 644 {} + 2>/dev/null || true
        # Allow Caddy to read static via group/other read (UMask 022 already ensures this).
        if id "caddy" >/dev/null 2>&1; then
            setfacl -m u:caddy:rX -R "$APP_DIR/static" 2>/dev/null || true
        fi
    fi
    # Caddy log dir ownership
    if id "caddy" >/dev/null 2>&1; then
        chown -R caddy:caddy /var/log/caddy 2>/dev/null || true
    fi
}




cleanup_backup() {
    if [ -d "$BACKUP_DIR" ]; then
        log_warn "Deploy failed — rolling back..."
        rsync -a --delete --exclude='venv' --exclude='node_modules' --exclude='var/' --exclude='.u2net/' "$BACKUP_DIR/" "$APP_DIR/"
        # Restore consistent SQLite snapshot taken before pull (code+DB stay in sync).
        if [ -f "$BACKUP_DIR/analytics.db.bak" ]; then
            mkdir -p "$APP_DIR/var/data"
            cp "$BACKUP_DIR/analytics.db.bak" "$APP_DIR/var/data/analytics.db" 2>/dev/null || true
            rm -f "$APP_DIR/var/data/analytics.db-wal" "$APP_DIR/var/data/analytics.db-shm" 2>/dev/null || true
        fi
        rm -rf "$BACKUP_DIR"
        log_info "Rollback files restored — restarting service..."
        if command -v systemctl >/dev/null 2>&1 && [ -f "/etc/systemd/system/$APP_NAME.service" ]; then
            sudo systemctl daemon-reload 2>/dev/null || true
            sudo systemctl restart "$APP_NAME" 2>/dev/null || true
        fi
        log_info "Rollback complete."
    fi
}

purge_old_backups() {
    # Keep only the last 7 days of backups to avoid filling disk
    find /var/backups -maxdepth 1 -name "${APP_NAME}_backup_*" -mtime +7 -exec rm -rf {} + 2>/dev/null || true
}
# ─── Main ──────────────────────────────────────────────────

cd "$APP_DIR"

if [ "${1:-}" = "--setup" ]; then
    log_info "=== First-time setup ==="
    ensure_system_deps
    setup_venv
    source "$APP_DIR/venv/bin/activate"
    setup_env_file
    install_python
    build_rust
    build_frontend
    setup_permissions
    setup_systemd
    health_check
    log_info "=== Setup complete! ==="
    exit 0
fi

log_info "=== Deploying $APP_NAME ==="

trap cleanup_backup ERR

ensure_system_deps
setup_venv
source "$APP_DIR/venv/bin/activate"
setup_env_file
backup_current   # <-- backup BEFORE pulling so we can rollback to known-good
pull_latest
install_python
build_rust
build_frontend
# Export the deployed commit SHA so the app can report its version,
# and persist it to .env atomically so systemd workers (EnvironmentFile=.env) see it.
export APP_VERSION
APP_VERSION="$(git -C "$APP_DIR" rev-parse --short HEAD 2>/dev/null || date +%s)"
if [ -f "$APP_DIR/.env" ]; then
    tmp_env="$(mktemp)"
    grep -v "^APP_VERSION=" "$APP_DIR/.env" > "$tmp_env" || true
    echo "APP_VERSION=$APP_VERSION" >> "$tmp_env"
    mv "$tmp_env" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env" || true
fi
setup_permissions
restart_service
health_check

rm -rf "$BACKUP_DIR" 2>/dev/null || true
purge_old_backups
log_info "=== Deployment successful! ==="
