#!/usr/bin/env bash
# ============================================================
# run.sh — Single entry point: git pull → install → run
# Usage:
#   First time on VPS:  bash run.sh
#   Subsequent deploys: bash run.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="storybrain-ai"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ─── 1. Pull latest from GitHub ────────────────────────────
if git remote -v >/dev/null 2>&1; then
    log_info "Pulling latest code from GitHub..."
    git fetch origin
    git reset --hard origin/main
    log_info "Updated to $(git log -1 --format='%h %s')"
fi

# ─── 2. Install missing system dependencies ─────────────────
log_info "Checking and installing system dependencies..."
MISSING=""
for cmd in python3 pip3 node npm; do
    command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done

if [ -n "$MISSING" ]; then
    log_info "Installing missing: $MISSING"
    sudo apt-get update -qq
    # Python3 & pip
    command -v python3 >/dev/null 2>&1 || sudo apt-get install -y -qq python3 python3-pip python3-venv
    # Node.js 20 LTS
    if ! command -v node >/dev/null 2>&1; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y -qq nodejs
    fi
    # Rust (only if rust_predictor exists)
    if [ -d "rust_predictor" ] && ! command -v rustc >/dev/null 2>&1; then
        log_info "Installing Rust..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
    fi
fi

# ─── 3. Create Python venv if needed ───────────────────────
if [ ! -d "venv" ]; then
    log_info "Creating Python virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# ─── 4. Create .env from example if missing ─────────────────
if [ ! -f ".env" ]; then
    log_info "Creating .env from .env.example..."
    cp .env.example .env
    # Generate a random SECRET_KEY
    if command -v python3 >/dev/null 2>&1; then
        SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        if grep -q "^SECRET_KEY=" .env.example 2>/dev/null; then
            sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET/" .env
        fi
    fi
    log_warn "IMPORTANT: Edit .env with your production domain settings!"
    log_warn "  Set: ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com"
    log_warn "  Set: CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com"
fi

# ─── 5. Load .env ──────────────────────────────────────────
set -a; source .env; set +a

# ─── 6. Deploy ─────────────────────────────────────────────
bash deploy.sh
