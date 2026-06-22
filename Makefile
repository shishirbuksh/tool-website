.PHONY: install build start run clean deploy setup-docker setup-vps

install:
	@echo "=== Installing Python dependencies ==="
	pip install -r requirements.txt
	@echo "=== Installing Node.js dependencies ==="
	npm ci
	@echo "=== Building Rust extension ==="
	cd rust_predictor && pip install -e .
	@echo "=== Install complete ==="

build:
	@echo "=== Building frontend assets ==="
	npm run build
	@echo "=== Build complete ==="

start:
	@echo "=== Starting production server ==="
	gunicorn app.main:app -c gunicorn_conf.py

run: install build start

deploy:
	@echo "=== Running full deploy pipeline ==="
	bash deploy.sh

setup-docker:
	@echo "=== Starting with Docker Compose ==="
	docker compose up -d --build

setup-vps:
	@echo "=== One-command VPS setup ==="
	bash deploy.sh --setup

test:
	@echo "=== Running tests ==="
	python -m pytest tests/ -v --tb=short

clean:
	@echo "=== Cleaning build artifacts ==="
	rm -rf node_modules/
	rm -rf rust_predictor/target/
	rm -rf static/js/app.js static/js/tools.js static/js/tools.utils.js
	rm -rf static/css/app.css static/fonts/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".tox" -exec rm -rf {} + 2>/dev/null || true
	@echo "=== Clean complete ==="
