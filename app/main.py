import asyncio
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    analytics,
    blog,
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
    # Startup warmup + background reaper.
    # NOTE: JobService task_timeout (90s) must stay < gunicorn worker
    # timeout (gunicorn_conf.py TIMEOUT, default 320s) or gunicorn
    # will kill workers mid-job.
    _startup_logger.info("Lifespan startup: warming caches")
    try:
        from app.core.tool_data import ToolDataLoader  # noqa: PLC0415

        ToolDataLoader.get_all()
        _startup_logger.info("ToolDataLoader warmed")
    except Exception:
        _startup_logger.exception("ToolDataLoader warmup failed")
    # Lazily pre-import heavy optional deps so first request doesn't pay
    # cold-start cost (and logs clearly when missing).
    for _mod in ("rembg", "cv2", "prophet"):
        try:
            __import__(_mod)
            _startup_logger.info("Pre-imported optional dep: %s", _mod)
        except Exception:
            _startup_logger.warning("Optional dep %s not available at startup", _mod)
    try:
        import app.services.analytics_service as analytics_svc  # noqa: PLC0415

        # Trigger pool init (creates DB + WAL/busy_timeout pragmas).
        analytics_svc.get_counts(limit=1)
        _startup_logger.info("Analytics pool initialized")
    except Exception:
        _startup_logger.exception("Analytics pool init failed")
    # Background reaper for finished jobs (interval-gated _maybe_cleanup).
    _reaper = None
    try:
        from app.services.job_service import get_job_service  # noqa: PLC0415

        _reaper = asyncio.create_task(get_job_service().cleanup_loop())
    except Exception:
        _startup_logger.exception("Failed to start job cleanup_loop")
    try:
        yield
    finally:
        if _reaper is not None:
            _reaper.cancel()
            try:
                await _reaper
            except asyncio.CancelledError:
                pass
            except Exception:
                _startup_logger.exception("Error during job cleanup_loop shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

# NOTE: Starlette builds the stack so the LAST added middleware is outermost.
# TrustedHost must be outermost to reject untrusted Host headers first.
# RateLimit/MaxBodySize run just inside it so floods are shed before GZip/CORS work.
hosts = settings.allowed_hosts_list

app.add_middleware(OriginCheckMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(NoIndexAPIMiddleware)
app.add_middleware(CaseSensitiveRedirectMiddleware)

app.add_middleware(RequestIDMiddleware)
# ROUND-2 perf: GZip for dynamic responses only; Caddy serves precompressed
# static (.br/.gz from scripts/compress.js) directly — no app code needed.
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "Accept",
        "Origin",
    ],
    expose_headers=["X-Request-ID", "Content-Disposition"],
    max_age=600,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MaxBodySizeMiddleware, max_size=max(settings.IMAGE_MAX_SIZE, settings.PDF_MAX_SIZE))
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
# TrustedHost outermost (added last) so Host validation runs first.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts or ["127.0.0.1", "localhost"])

register_exception_handlers(app)

try:
    os.makedirs(os.path.join(settings.static_dir, "css"), exist_ok=True)
    os.makedirs(os.path.join(settings.static_dir, "js"), exist_ok=True)
    os.makedirs(os.path.join(settings.templates_dir, "tools"), exist_ok=True)
except OSError as exc:
    _startup_logger.warning("Failed to create directories", exc_info=exc)


class CachedStaticFiles(StaticFiles):
    _lm_cache: dict[str, tuple[str, float]] = {}
    _LM_TTL = 300
    _LM_MAX = 2000

    async def _get_mtime(self, full_path: str) -> float | None:
        loop = asyncio.get_running_loop()
        try:
            stat_result = await loop.run_in_executor(None, os.stat, full_path)
            return stat_result.st_mtime
        except OSError:
            return None

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            # Service worker must never be cached immutably
            if path == "sw.js" or path.endswith("/sw.js"):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Service-Worker-Allowed"] = "/"
            elif path in ("manifest.json", "ads.txt"):
                response.headers["Cache-Control"] = "public, max-age=86400"
            else:
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

            if response.status_code == 200:
                import time as _time

                now = _time.time()
                cached = self._lm_cache.get(path)
                if cached is None or (now - cached[1]) > self._LM_TTL:
                    mtime = await self._get_mtime(os.path.join(settings.static_dir, path))
                    if mtime is not None:
                        if len(self._lm_cache) >= self._LM_MAX:
                            # Evict oldest entry to bound memory.
                            oldest = min(self._lm_cache.items(), key=lambda kv: kv[1][1])[0]
                            self._lm_cache.pop(oldest, None)
                        self._lm_cache[path] = (
                            datetime.fromtimestamp(mtime, tz=UTC).strftime("%a, %d %b %Y %H:%M:%S GMT"),
                            now,
                        )
                if path in self._lm_cache:
                    response.headers["Last-Modified"] = self._lm_cache[path][0]
        return response


app.mount("/static", CachedStaticFiles(directory=settings.static_dir), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join(settings.static_dir, "favicon.ico")
    if not os.path.isfile(favicon_path):
        raise HTTPException(status_code=404, detail="favicon.ico not found")
    return FileResponse(
        favicon_path,
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"},
    )


@app.get("/ads.txt", include_in_schema=False)
async def ads_txt():
    ads_path = os.path.join(settings.static_dir, "ads.txt")
    if not os.path.isfile(ads_path):
        raise HTTPException(status_code=404, detail="ads.txt not found")
    return FileResponse(
        ads_path,
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=3600"},
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
app.include_router(blog.router)
app.include_router(pages.router)
app.include_router(tools_image.router)
app.include_router(tools_pdf.router)
app.include_router(tools_crypto.router)
app.include_router(tools_fng.router)
app.include_router(tools_proxy.router)
app.include_router(tools_nft.router)
app.include_router(analytics.router)
app.include_router(jobs_router.router)
