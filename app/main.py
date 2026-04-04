import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.routes import pages, tools

app = FastAPI(title=settings.PROJECT_NAME)

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
app.include_router(tools.router)
app.include_router(pages.router)
