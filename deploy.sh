#!/usr/bin/env bash
# ============================================================
# deploy.sh — One-command production deploy from GitHub to VPS
# Usage: bash deploy.sh
# First time:  bash deploy.sh --setup
# ============================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="storybrain-ai"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/tmp/${APP_NAME}_backup_${TIMESTAMP}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cleanup() {
    if [ -d "$BACKUP_DIR" ]; then
        log_warn "Rolling back to previous version..."
        rsync -a "$BACKUP_DIR/" "$APP_DIR/"
        rm -rf "$BACKUP_DIR"
        log_info "Rollback complete."
    fi
}
trap cleanup ERR

ensure_deps() {
    log_info "Checking system dependencies..."
    local missing=()
    command -v python3    >/dev/null 2>&1 || missing+=("python3")
    command -v pip3       >/dev/null 2>&1 || missing+=("pip3")
    command -v node       >/dev/null 2>&1 || missing+=("nodejs")
    command -v npm        >/dev/null 2>&1 || missing+=("npm")
    command -v rustc      >/dev/null 2>&1 || missing+=("rustc")
    command -v cargo      >/dev/null 2>&1 || missing+=("cargo")

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing: ${missing[*]}"
        log_info "Install with: sudo apt install -y python3 python3-pip nodejs npm rustc cargo"
        exit 1
    fi
}

setup_env() {
    if [ ! -f "$APP_DIR/.env" ]; then
        log_info "Creating .env from .env.example..."
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        log_warn "Edit .env with your settings before running in production!"
    fi
}

backup_current() {
    log_info "Backing up current version to $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    rsync -a --exclude='node_modules' \
             --exclude='venv' \
             --exclude='venv_new' \
             --exclude='.git' \
             --exclude='rust_predictor/target' \
             --exclude='__pycache__' \
             "$APP_DIR/" "$BACKUP_DIR/"
}

pull_latest() {
    log_info "Pulling latest code from GitHub..."
    git -C "$APP_DIR" fetch origin
    git -C "$APP_DIR" reset --hard origin/main
}

install_python() {
    log_info "Installing Python dependencies..."
    pip3 install -q --no-cache-dir -r "$APP_DIR/requirements.txt"
}

install_node() {
    log_info "Installing Node.js dependencies..."
    npm ci --silent --prefix "$APP_DIR"
}

build_rust() {
    log_info "Building Rust extension..."
    cd "$APP_DIR/rust_predictor"
    pip3 install -q -e .
    cd "$APP_DIR"
}

build_frontend() {
    log_info "Building frontend assets..."
    npm --prefix "$APP_DIR" run build
}

restart_service() {
    log_info "Restarting application service..."
    if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet "$APP_NAME" 2>/dev/null; then
        sudo systemctl restart "$APP_NAME"
        log_info "Service restarted via systemd."
    elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        docker compose -f "$APP_DIR/docker-compose.yml" up -d --build
        log_info "Stack restarted via Docker Compose."
    else
        log_warn "No service manager found. Start manually: cd $APP_DIR && gunicorn app.main:app -c gunicorn_conf.py"
    fi
}

health_check() {
    local port="${PORT:-8090}"
    local max_retries=12
    local retry=0

    log_info "Running health check on port $port..."
    sleep 2

    while [ $retry -lt $max_retries ]; do
        if curl -sf "http://127.0.0.1:$port/healthz" >/dev/null 2>&1; then
            echo ""
            log_info "Application is healthy! ✓"
            return 0
        fi
        retry=$((retry + 1))
        echo -n "."
        sleep 2
    done
    echo ""
    log_error "Health check failed after $max_retries attempts."
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

# ─── main ──────────────────────────────────────────────────
cd "$APP_DIR"

if [ "${1:-}" = "--setup" ]; then
    ensure_deps
    setup_env
    setup_systemd
    install_python
    install_node
    build_rust
    build_frontend
    restart_service
    health_check
    log_info "Setup complete! Application is running."
    exit 0
fi

log_info "=== Deploying $APP_NAME ==="
ensure_deps
setup_env
backup_current
pull_latest
install_python
install_node
build_rust
build_frontend
restart_service
health_check

# Clean up backup on success
rm -rf "$BACKUP_DIR"
log_info "=== Deployment successful! ==="
