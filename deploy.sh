#!/usr/bin/env bash
# ============================================================
# deploy.sh — Production deploy engine
# Called by run.sh. Can also run standalone.
# Installs deps, builds assets, restarts service, health check.
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

# Activate venv if exists (set up by run.sh)
if [ -f "$APP_DIR/venv/bin/activate" ]; then
    source "$APP_DIR/venv/bin/activate"
fi

cleanup() {
    if [ -d "$BACKUP_DIR" ]; then
        log_warn "Rolling back to previous version..."
        rsync -a --exclude='venv' --exclude='node_modules' "$BACKUP_DIR/" "$APP_DIR/"
        rm -rf "$BACKUP_DIR"
        log_info "Rollback complete."
    fi
}
trap cleanup ERR

# ─── Install steps ────────────────────────────────────────

install_python() {
    log_info "Installing Python dependencies..."
    pip install -q --no-cache-dir -r "$APP_DIR/requirements.txt"
}

install_node() {
    log_info "Installing Node.js dependencies..."
    npm ci --silent --prefix "$APP_DIR" 2>/dev/null || npm install --silent --prefix "$APP_DIR"
}

build_rust() {
    if [ -d "$APP_DIR/rust_predictor" ] && [ -f "$APP_DIR/rust_predictor/Cargo.toml" ]; then
        log_info "Building Rust extension..."
        pip install -q -e "$APP_DIR/rust_predictor" 2>/dev/null || log_warn "Rust build skipped (maturin/pyproject issue)"
    fi
}

build_frontend() {
    log_info "Building frontend assets..."
    npm --prefix "$APP_DIR" run build 2>/dev/null || log_warn "Frontend build skipped (check package.json)"
}

setup_env_file() {
    if [ ! -f "$APP_DIR/.env" ]; then
        if [ -f "$APP_DIR/.env.example" ]; then
            cp "$APP_DIR/.env.example" "$APP_DIR/.env"
            log_warn ".env created from .env.example — edit it with your settings"
        fi
    fi
}

backup_current() {
    log_info "Backing up current version..."
    mkdir -p "$BACKUP_DIR"
    rsync -a --exclude='node_modules' --exclude='venv' --exclude='venv_new' \
             --exclude='.git' --exclude='rust_predictor/target' --exclude='__pycache__' \
             --exclude='*.pyc' --exclude='.pytest_cache' --exclude='.ruff_cache' \
             "$APP_DIR/" "$BACKUP_DIR/"
}

restart_service() {
    log_info "Restarting application..."
    if command -v systemctl >/dev/null 2>&1 && systemctl is-enabled "$APP_NAME" >/dev/null 2>&1; then
        sudo systemctl restart "$APP_NAME"
        log_info "Service restarted via systemd."
    elif command -v docker >/dev/null 2>&1 && [ -f "$APP_DIR/docker-compose.yml" ]; then
        docker compose -f "$APP_DIR/docker-compose.yml" up -d --build
        log_info "Stack restarted via Docker Compose."
    else
        # Start directly if no service manager
        log_info "Starting gunicorn directly..."
        pkill -f "gunicorn.*$APP_NAME" 2>/dev/null || true
        nohup gunicorn app.main:app -c "$APP_DIR/gunicorn_conf.py" > /tmp/${APP_NAME}.log 2>&1 &
        log_info "Gunicorn started (PID: $!). Log: /tmp/${APP_NAME}.log"
    fi
}

health_check() {
    local port="${PORT:-8090}"
    local max_retries=15
    local retry=0
    log_info "Waiting for app on port $port..."
    while [ $retry -lt $max_retries ]; do
        if curl -sf "http://127.0.0.1:$port/healthz" >/dev/null 2>&1; then
            log_info "Application is healthy! ✓"
            return 0
        fi
        retry=$((retry + 1))
        sleep 2
    done
    log_error "Health check failed — app not responding on port $port"
    log_info "Check logs: journalctl -u $APP_NAME -n 50 --no-pager"
    return 1
}

setup_systemd() {
    log_info "Installing systemd service..."
    sudo cp "$APP_DIR/storybrain-ai.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable "$APP_NAME"
    sudo systemctl start "$APP_NAME"
    log_info "systemd service installed and started."
}

# ─── Main ──────────────────────────────────────────────────
cd "$APP_DIR"
setup_env_file

if [ "${1:-}" = "--setup" ]; then
    setup_systemd
    install_python
    install_node
    build_rust
    build_frontend
    restart_service
    health_check
    log_info "Setup complete!"
    exit 0
fi

log_info "=== Deploying $APP_NAME ==="
backup_current
install_python
install_node
build_rust
build_frontend
restart_service
health_check
rm -rf "$BACKUP_DIR"
log_info "=== Deployment successful! ==="
