#!/usr/bin/env bash
# ============================================================
# deploy.sh — Production deploy engine for StoryBrain AI
#
# First time:  sudo bash deploy.sh --setup
# Every time:  sudo bash deploy.sh
# ============================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="storybrain-ai"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/tmp/${APP_NAME}_backup_${TIMESTAMP}"

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
    for cmd in python3 pip3 node npm; do
        command -v "$cmd" >/dev/null 2>&1 || missing="$missing $cmd"
    done
    if [ -n "$missing" ]; then
        log_info "Installing missing system deps: $missing"
        command -v python3 >/dev/null 2>&1 || sudo apt-get install -y -qq python3 python3-pip python3-venv
        if ! command -v node >/dev/null 2>&1; then
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            sudo apt-get install -y -qq nodejs
        fi
    fi
}

fix_service_paths() {
    local svc="$APP_DIR/storybrain-ai.service"
    local tmp_svc="/tmp/${APP_NAME}.service"
    if [ -f "$svc" ]; then
        sed "s|{{APP_DIR}}|$APP_DIR|g" "$svc" > "$tmp_svc"
        echo "$tmp_svc"
    else
        echo ""
    fi
}

install_python() {
    log_info "Installing Python core dependencies..."
    pip install -q --no-cache-dir -r "$APP_DIR/requirements.txt"
    log_info "Installing optional heavy dependencies (may warn, not fatal)..."
    for pkg in "rembg[cpu]" "opencv-python-headless" "prophet"; do
        pip install -q "$pkg" 2>/dev/null || log_warn "Optional dep skipped: $pkg"
    done
}

install_node() {
    log_info "Installing Node.js dependencies..."
    npm ci --silent --prefix "$APP_DIR" 2>/dev/null || npm install --silent --prefix "$APP_DIR"
}

build_rust() {
    if [ -f "$APP_DIR/rust_predictor/Cargo.toml" ]; then
        log_info "Building Rust extension..."
        pip install -q maturin 2>/dev/null || true
        pip install -q -e "$APP_DIR/rust_predictor" 2>/dev/null && log_info "Rust extension built" || log_warn "Rust build skipped"
    fi
}

build_frontend() {
    if [ -f "$APP_DIR/package.json" ]; then
        log_info "Building frontend assets..."
        npm --prefix "$APP_DIR" run build 2>/dev/null || log_warn "Frontend build skipped"
    fi
}

backup_current() {
    if [ ! -d "$APP_DIR/.git" ]; then
        log_warn "No .git found — skipping backup (fresh clone)"
        return
    fi
    log_info "Backing up current version..."
    mkdir -p "$BACKUP_DIR"
    rsync -a --exclude='node_modules' --exclude='venv' --exclude='.git' \
             --exclude='rust_predictor/target' --exclude='__pycache__' \
             --exclude='*.pyc' --exclude='.pytest_cache' --exclude='.ruff_cache' \
             "$APP_DIR/" "$BACKUP_DIR/"
}

pull_latest() {
    if [ ! -d "$APP_DIR/.git" ]; then
        log_warn "No .git found — skipping git pull"
        return
    fi
    log_info "Pulling latest from GitHub..."
    git -C "$APP_DIR" fetch origin
    git -C "$APP_DIR" reset --hard origin/main
    log_info "Updated to $(git -C "$APP_DIR" log -1 --format='%h %s')"
}

restart_service() {
    if command -v systemctl >/dev/null 2>&1 && [ -f "/etc/systemd/system/$APP_NAME.service" ]; then
        log_info "Restarting systemd service..."
        sudo systemctl restart "$APP_NAME"
        log_info "Service restarted."
    else
        log_info "No systemd service found — starting gunicorn directly..."
        pkill -f "gunicorn.*$APP_NAME" 2>/dev/null || true
        cd "$APP_DIR"
        nohup "$APP_DIR/venv/bin/gunicorn" app.main:app -c "$APP_DIR/gunicorn_conf.py" > /tmp/${APP_NAME}.log 2>&1 &
        log_info "Gunicorn started (PID: $!). Log: /tmp/${APP_NAME}.log"
    fi
}

health_check() {
    local port="${PORT:-8090}"
    local retries=15
    log_info "Health check on port $port..."
    for i in $(seq 1 $retries); do
        if curl -sf "http://127.0.0.1:$port/healthz" >/dev/null 2>&1; then
            log_info "Application is healthy! ✓"
            return 0
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
}

setup_env_file() {
    if [ ! -f "$APP_DIR/.env" ]; then
        if [ -f "$APP_DIR/.env.example" ]; then
            cp "$APP_DIR/.env.example" "$APP_DIR/.env"
            SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me")
            if command -v python3 >/dev/null 2>&1; then
                sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" "$APP_DIR/.env"
            fi
            log_warn ".env created — edit it: nano $APP_DIR/.env"
            log_warn "  Set: ALLOWED_HOSTS=www.storybrainai.com,storybrainai.com"
            log_warn "  Set: CORS_ORIGINS=https://www.storybrainai.com,https://storybrainai.com"
        fi
    fi
    set -a; source "$APP_DIR/.env"; set +a
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

setup_caddy() {
    log_info "Setting up Caddy..."
    if ! command -v caddy >/dev/null 2>&1; then
        log_info "Installing Caddy from official repository..."
        sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
        sudo apt-get update -qq
        sudo apt-get install -y -qq caddy
    fi
    if [ -f "$APP_DIR/Caddyfile" ]; then
        log_info "Applying Caddyfile configuration..."
        sudo cp "$APP_DIR/Caddyfile" /etc/caddy/Caddyfile
        sudo systemctl reload caddy || sudo systemctl restart caddy
    fi
}

cleanup_backup() {
    if [ -d "$BACKUP_DIR" ]; then
        log_warn "Deploy failed — rolling back..."
        rsync -a --exclude='venv' --exclude='node_modules' "$BACKUP_DIR/" "$APP_DIR/"
        rm -rf "$BACKUP_DIR"
        log_info "Rollback complete."
    fi
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
    install_node
    build_rust
    build_frontend
    setup_systemd
    setup_caddy
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
pull_latest
backup_current
install_python
install_node
build_rust
build_frontend
setup_caddy
restart_service
health_check

rm -rf "$BACKUP_DIR" 2>/dev/null || true
log_info "=== Deployment successful! ==="
