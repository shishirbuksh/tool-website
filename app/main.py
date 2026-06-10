import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

from app.core.config import settings
from app.api.routes import pages, tools, seo

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=None,  # Disabled for production
    redoc_url=None  # Disabled for production
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval';"
    return response

# Production Middlewares
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.storybrainai.com",
        "https://storybrainai.com",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
try:
    os.makedirs(os.path.join(settings.STATIC_DIR, "css"), exist_ok=True)
    os.makedirs(os.path.join(settings.STATIC_DIR, "js"), exist_ok=True)
    os.makedirs(os.path.join(settings.TEMPLATES_DIR, "tools"), exist_ok=True)
except OSError:
    pass  # Allow serverless/read-only production environments to proceed

# Mount static folder with caching headers
class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

app.mount("/static", CachedStaticFiles(directory=settings.STATIC_DIR), name="static")

# Include routers
app.include_router(seo.router)
app.include_router(tools.router)
app.include_router(pages.router)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(settings.STATIC_DIR, "favicon.svg"))
