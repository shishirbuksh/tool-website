import logging
import multiprocessing
import os

host = os.getenv("HOST", "127.0.0.1")
port = os.getenv("PORT", "8090")
bind = f"{host}:{port}"

cores = multiprocessing.cpu_count()
workers_per_core = float(os.getenv("WORKERS_PER_CORE", "1"))
default_web_concurrency = workers_per_core * cores + 1
# WORKERS=0 (or any value <= 0) means "auto": cores + 1. This matches the
# .env.example convention (WORKERS=0 = auto) instead of clamping to 2.
_requested_workers = int(float(os.getenv("WORKERS", str(default_web_concurrency))))
if _requested_workers <= 0:
    web_concurrency = int(default_web_concurrency)
else:
    web_concurrency = _requested_workers
workers = max(int(web_concurrency), 2)

worker_class = "uvicorn.workers.UvicornWorker"
max_requests = 10000
max_requests_jitter = 1000
loglevel = os.getenv("LOG_LEVEL", "info").lower()

accesslog = "-"
errorlog = "-"

timeout = int(os.getenv("TIMEOUT", "320"))  # MUST stay > JobService task_timeout (90s). 320s allows rembg/prophet cold starts.
keepalive = int(os.getenv("KEEP_ALIVE", "5"))
graceful_timeout = int(os.getenv("GRACEFUL_TIMEOUT", "110"))
worker_tmp_dir = "/dev/shm"
limit_request_line = 8190
limit_request_fields = 100

# SECURITY: "*" trusts any X-Forwarded-For sender, allowing IP spoofing of
# internal-guarded endpoints (/metrics, /api/analytics/top). In production set
# FORWARDED_ALLOW_IPS to your trusted reverse proxy only, e.g. "127.0.0.1".
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
proxy_allow_ips = os.getenv("PROXY_ALLOW_IPS", "127.0.0.1")

logging.basicConfig(level=logging.INFO)
logging.info(
    "Starting server: %s | workers=%d | loglevel=%s | timeout=%s",
    bind,
    workers,
    loglevel,
    timeout,
)
