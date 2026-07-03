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
    for cmd in python3 pip3; do
        command -v "$cmd" >/dev/null 2>&1 || missing="$missing $cmd"
    done
    if [ -n "$missing" ]; then
        log_info "Installing missing system deps: $missing"
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3 python3-pip python3-venv libgomp1 libglib2.0-0
    else
        # Just to be safe, ensure these libraries exist for OpenCV/onnxruntime
        sudo apt-get install -y -qq libgomp1 libglib2.0-0 >/dev/null 2>&1 || true
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
    
    # Install heavy optional dependencies (rembg)
    if ! python3 -c "import rembg" 2>/dev/null; then
        log_info "Installing heavy optional dependency: rembg[cpu]"
        pip install -q "rembg[cpu]"
    fi

    # Install opencv for watermark remover
    if ! python3 -c "import cv2" 2>/dev/null; then
        log_info "Installing OpenCV..."
        pip install -q opencv-python-headless
    fi

    # Pre-download rembg models so gunicorn workers don't timeout
    if python3 -c "import rembg" 2>/dev/null; then
        log_info "Pre-downloading rembg models..."
        export U2NET_HOME="$APP_DIR/.u2net"
        python3 -c "from rembg import new_session; new_session('u2netp'); new_session('u2net')" >/dev/null 2>&1 || true
    fi
}

build_rust() {
    if [ -f "$APP_DIR/rust_predictor/Cargo.toml" ]; then
        log_info "Building Rust extension..."
        pip install -q maturin 2>/dev/null || true
        pip install -q -e "$APP_DIR/rust_predictor" 2>/dev/null && log_info "Rust extension built" || log_warn "Rust build skipped"
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
        log_info "Updating and restarting systemd service..."
        local fixed=$(fix_service_paths)
        if [ -n "$fixed" ]; then
            sudo cp "$fixed" /etc/systemd/system/$APP_NAME.service
            sudo systemctl daemon-reload
            rm -f "$fixed"
        fi
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

setup_permissions() {
    log_info "Ensuring required directories exist..."
    mkdir -p "$APP_DIR/var" "$APP_DIR/.u2net"
    
    if id "storybrainai" >/dev/null 2>&1; then
        log_info "Fixing permissions (chown storybrainai:storybrainai)..."
        chown -R storybrainai:storybrainai "$APP_DIR"
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
# Export the deployed commit SHA so the app can report its version
export APP_VERSION
APP_VERSION="$(git -C "$APP_DIR" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
setup_permissions
restart_service
health_check

rm -rf "$BACKUP_DIR" 2>/dev/null || true
purge_old_backups
log_info "=== Deployment successful! ==="
