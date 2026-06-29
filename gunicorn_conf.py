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
loglevel = os.getenv("LOG_LEVEL", "info").lower()

accesslog = "-"
errorlog = "-"

timeout = int(os.getenv("TIMEOUT", "120"))
keepalive = int(os.getenv("KEEP_ALIVE", "5"))

forwarded_allow_ips = "127.0.0.1"
proxy_allow_ips = "127.0.0.1"

logging.basicConfig(level=logging.INFO)
logging.info(
    "Starting server: %s | workers=%d | loglevel=%s | timeout=%s",
    bind,
    workers,
    loglevel,
    timeout,
)
