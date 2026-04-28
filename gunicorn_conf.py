import multiprocessing
import os

# Gunicorn configuration optimized for Uvicorn/FastAPI production deployment
# Run using: gunicorn -c gunicorn_conf.py main:app

# Server Socket
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "8000")
bind = f"{host}:{port}"

# Worker Processes
# Calculate optimal number of workers based on CPU cores
cores = multiprocessing.cpu_count()
workers_per_core = float(os.getenv("WORKERS_PER_CORE", "1"))
default_web_concurrency = workers_per_core * cores
web_concurrency = int(os.getenv("WEB_CONCURRENCY", str(default_web_concurrency)))

# Minimum of 2 workers to prevent single-worker blocking
workers = max(int(web_concurrency), 2)

# Uvicorn worker class for ASGI apps
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-"  # Output to stdout
errorlog = "-"   # Output to stderr

# Timeouts
timeout = int(os.getenv("TIMEOUT", "120"))
keepalive = int(os.getenv("KEEP_ALIVE", "5"))

print(f"Starting Gunicorn with {workers} workers at {bind}")
