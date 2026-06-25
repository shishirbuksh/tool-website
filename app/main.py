import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.log import setup_logging
from app.core.metrics import MetricsMiddleware
from app.core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware

setup_logging()
from app.api.routes import (
    analytics,
    health,
    pages,
    seo,
    tools_b64,
    tools_crypto,
    tools_fng,
    tools_image,
    tools_nft,
    tools_pdf,
    tools_proxy,
    tools_qr,
)
from app.api.routes import jobs as jobs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

register_exception_handlers(app)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    os.makedirs(os.path.join(settings.STATIC_DIR, "css"), exist_ok=True)
    os.makedirs(os.path.join(settings.STATIC_DIR, "js"), exist_ok=True)
    os.makedirs(os.path.join(settings.TEMPLATES_DIR, "tools"), exist_ok=True)
except OSError:
    pass


class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


app.mount("/static", CachedStaticFiles(directory=settings.STATIC_DIR), name="static")

app.include_router(health.router)
app.include_router(seo.router)
app.include_router(pages.router)
app.include_router(tools_qr.router)
app.include_router(tools_image.router)
app.include_router(tools_pdf.router)
app.include_router(tools_crypto.router)
app.include_router(tools_fng.router)
app.include_router(tools_proxy.router)
app.include_router(tools_nft.router)
app.include_router(tools_b64.router)
app.include_router(analytics.router)
app.include_router(jobs_router.router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(settings.STATIC_DIR, "favicon.svg"))
