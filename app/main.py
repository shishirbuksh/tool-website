import asyncio
import os
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    analytics,
    health,
    pages,
    seo,
    tools_crypto,
    tools_fng,
    tools_image,
    tools_nft,
    tools_pdf,
    tools_proxy,
)
from app.api.routes import jobs as jobs_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.log import get_logger, setup_logging
from app.core.metrics import MetricsMiddleware
from app.core.middleware import (
    CaseSensitiveRedirectMiddleware,
    MaxBodySizeMiddleware,
    NoIndexAPIMiddleware,
    OriginCheckMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

_startup_logger = get_logger("app.main")
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

hosts = settings.allowed_hosts_list
app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts or ["127.0.0.1", "localhost"])
app.add_middleware(CaseSensitiveRedirectMiddleware)
app.add_middleware(MaxBodySizeMiddleware, max_size=10 * 1024 * 1024)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(OriginCheckMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(NoIndexAPIMiddleware)

register_exception_handlers(app)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "Accept",
        "Origin",
    ],
)

try:
    os.makedirs(os.path.join(settings.static_dir, "css"), exist_ok=True)
    os.makedirs(os.path.join(settings.static_dir, "js"), exist_ok=True)
    os.makedirs(os.path.join(settings.templates_dir, "tools"), exist_ok=True)
except OSError as exc:
    _startup_logger.warning("Failed to create directories", exc_info=exc)


class CachedStaticFiles(StaticFiles):
    _lm_cache: dict[str, str] = {}

    async def _get_mtime(self, full_path: str) -> float:
        loop = asyncio.get_running_loop()
        try:
            stat_result = await loop.run_in_executor(None, os.stat, full_path)
            return stat_result.st_mtime
        except OSError:
            return time.time()

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            if path not in self._lm_cache:
                mtime = await self._get_mtime(os.path.join(settings.static_dir, path))
                self._lm_cache[path] = datetime.fromtimestamp(mtime, tz=UTC).strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                )
            response.headers["Last-Modified"] = self._lm_cache[path]
        return response


app.mount("/static", CachedStaticFiles(directory=settings.static_dir), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(
        os.path.join(settings.static_dir, "favicon.ico"),
        media_type="image/x-icon",
    )


@app.get("/service-worker", include_in_schema=False)
async def service_worker():
    return FileResponse(
        os.path.join(settings.static_dir, "sw.js"),
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Service-Worker-Allowed": "/"
        }
    )


app.include_router(health.router)
app.include_router(seo.router)
app.include_router(pages.router)
app.include_router(tools_image.router)
app.include_router(tools_pdf.router)
app.include_router(tools_crypto.router)
app.include_router(tools_fng.router)
app.include_router(tools_proxy.router)
app.include_router(tools_nft.router)
app.include_router(analytics.router)
app.include_router(jobs_router.router)
