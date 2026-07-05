import logging
import multiprocessing
import os

host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "8090")
bind = f"{host}:{port}"

cores = multiprocessing.cpu_count()
workers_per_core = float(os.getenv("WORKERS_PER_CORE", "1"))
default_web_concurrency = workers_per_core * cores + 1
web_concurrency = int(float(os.getenv("WORKERS", str(default_web_concurrency))))
workers = max(int(web_concurrency), 2)

worker_class = "uvicorn.workers.UvicornWorker"
max_requests = 10000
max_requests_jitter = 1000
loglevel = os.getenv("LOG_LEVEL", "info").lower()

accesslog = "-"
errorlog = "-"

timeout = int(os.getenv("TIMEOUT", "120"))
keepalive = int(os.getenv("KEEP_ALIVE", "5"))

forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
proxy_allow_ips = os.getenv("PROXY_ALLOW_IPS", "*")

logging.basicConfig(level=logging.INFO)
logging.info(
    "Starting server: %s | workers=%d | loglevel=%s | timeout=%s",
    bind,
    workers,
    loglevel,
    timeout,
)
