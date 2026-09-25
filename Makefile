.PHONY: install build start run clean deploy setup-vps test coverage

# NOTE: do NOT `include .env` here — it leaks SECRET_KEY into `make -p`/subprocesses.
# Load locally with: set -a; source .env; set +a  (or direnv), then run make.

install:
	@echo "=== Installing Python dependencies ==="
	pip install -r requirements.txt
	@echo "=== Installing Node.js dependencies ==="
	npm ci
	@echo "=== Rust extension: skipped (pure Python MLP) ==="
	@echo "=== Install complete ==="

build:
	@echo "=== Building frontend assets ==="
	npm run build
	@echo "=== Build complete ==="

start:
	@echo "=== Starting production server ==="
	HOST=$${HOST:-127.0.0.1} PORT=$${PORT:-8090} gunicorn app.main:app -c gunicorn_conf.py

run: install build start

deploy:
	@echo "=== Running full deploy pipeline ==="
	bash deploy.sh

setup-vps:
	@echo "=== One-command VPS setup ==="
	bash deploy.sh --setup

test:
	@echo "=== Running tests ==="
	python -m pytest tests/ -v --tb=short --cov=app --cov-branch --cov-fail-under=80

coverage:
	@echo "=== Running tests with branch coverage ==="
	python -m coverage run -m pytest tests/ -v --tb=short
	python -m coverage report -m --fail-under=80
	python -m coverage html

clean:
	@echo "=== Cleaning build artifacts ==="
	@echo "[WARN] clean only removes node_modules and caches — tracked files under static/ are left intact"
	rm -rf node_modules/
	rm -rf rust_predictor/target/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".tox" -exec rm -rf {} + 2>/dev/null || true
	@echo "=== Clean complete ==="
