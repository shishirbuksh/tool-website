"""Gunicorn config for StoryBrain AI (FastAPI via UvicornWorker).

Env:
    HOST, PORT, WORKERS (0=auto: cores+1), WORKERS_PER_CORE,
    LOG_LEVEL, TIMEOUT, GRACEFUL_TIMEOUT, KEEP_ALIVE,
    FORWARDED_ALLOW_IPS, PROXY_ALLOW_IPS.

Timeout model: TIMEOUT must stay > JobService task_timeout (90s).
GRACEFUL_TIMEOUT should be close to TIMEOUT (e.g. 300 vs 320) so
in-flight rembg/prophet requests finish on graceful reload instead
of being SIGKILLed early (110s would cut 320s tasks short).
"""
import logging
import multiprocessing
import os

log = logging.getLogger(__name__)

host: str = os.getenv("HOST", "127.0.0.1")
port: str = os.getenv("PORT", "8090")
bind: str = f"{host}:{port}"

cores: int = multiprocessing.cpu_count()
workers_per_core: float = float(os.getenv("WORKERS_PER_CORE", "1"))
default_web_concurrency: float = workers_per_core * cores + 1
# WORKERS=0 (or any value <= 0) means "auto": cores + 1. This matches the
# .env.example convention (WORKERS=0 = auto) instead of clamping to 2.
_requested_workers: int = int(float(os.getenv("WORKERS", str(default_web_concurrency))))
if _requested_workers <= 0:
    web_concurrency: int = int(default_web_concurrency)
else:
    web_concurrency = _requested_workers
# Floor at 2: avoids single-worker fate-sharing (one slow ML task blocks all).
# OOM NOTE: each UvicornWorker holds torch/ML models in RAM — on small VPS
# (<=2GB) lower WORKERS or raise swap; floor of 2 can OOM with rembg loaded.
workers: int = max(int(web_concurrency), 2)

worker_class: str = "uvicorn.workers.UvicornWorker"
max_requests: int = 10000
max_requests_jitter: int = 1000
loglevel: str = os.getenv("LOG_LEVEL", "info").lower()

accesslog: str = "-"
errorlog: str = "-"

timeout: int = int(os.getenv("TIMEOUT", "320"))  # MUST stay > JobService task_timeout (90s). 320s allows rembg/prophet cold starts.
keepalive: int = int(os.getenv("KEEP_ALIVE", "5"))
# Keep GRACEFUL_TIMEOUT close to TIMEOUT (300 vs 320) so graceful reloads
# (SIGTERM/HUP) let in-flight requests finish; a small value (e.g. 110) would
# kill long ML tasks early and cause 502s on deploy.
graceful_timeout: int = int(os.getenv("GRACEFUL_TIMEOUT", "300"))
worker_tmp_dir: str = "/dev/shm"
limit_request_line: int = 8190
limit_request_fields: int = 100

# SECURITY: "*" trusts any X-Forwarded-For sender, allowing IP spoofing of
# internal-guarded endpoints (/metrics, /api/analytics/top). In production set
# FORWARDED_ALLOW_IPS to your trusted reverse proxy only, e.g. "127.0.0.1".
forwarded_allow_ips: str = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
proxy_allow_ips: str = os.getenv("PROXY_ALLOW_IPS", "127.0.0.1")


def on_starting(server) -> None:
    """Log bind summary on master start (no basicConfig at import)."""
    log.info(
        "Starting server: %s | workers=%d | loglevel=%s | timeout=%s",
        bind,
        workers,
        loglevel,
        timeout,
    )
