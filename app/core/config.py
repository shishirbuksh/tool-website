"""Application configuration via Pydantic Settings (env file + defaults).

Wiring notes (kept trivial on purpose):
- ``LOG_LEVEL`` is consumed by ``app.core.log.setup_logging`` / gunicorn
  (``gunicorn_conf.py`` reads ``LOG_LEVEL`` env directly).
- ``CACHE_DEFAULT_TTL`` is the fallback TTL used by
  ``app.core.cache.CacheService`` when callers pass no explicit TTL.
"""

import os

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _normalize_host(host: str) -> str:
    """Lowercase, strip whitespace/port for host comparison."""
    h = host.strip().lower()
    # Strip port if present (but keep IPv6 brackets handling simple).
    if h.startswith("["):
        # [::1]:8090 -> ::1
        end = h.find("]")
        if end != -1:
            return h[1:end]
        return h
    # host:port -> host (only when a single colon, to avoid mangling IPv6)
    if h.count(":") == 1:
        h = h.split(":", 1)[0]
    return h


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(_BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "Multi-Tool Website"
    HOST: str = "127.0.0.1"
    PORT: int = 8090
    LOG_LEVEL: str = "info"
    WORKERS: int = 0
    TIMEOUT: int = 320
    KEEP_ALIVE: int = 5
    REDIS_URL: str = ""
    ALLOWED_HOSTS: str = ""
    CORS_ORIGINS: str = ""
    SITE_URL: str = "https://www.storybrainai.com"
    IMAGE_MAX_SIZE: int = 10 * 1024 * 1024
    PDF_MAX_SIZE: int = 5 * 1024 * 1024
    ANALYTICS_RETENTION_DAYS: int = 90
    ANALYTICS_CLEANUP_INTERVAL: int = 300
    CACHE_DEFAULT_TTL: int = 300
    TRACK_ENABLED: bool = True
    CONTACT_EMAIL: str = ""
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 25
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SECRET_KEY: str = Field(default="", description="App secret key (sessions/signed URLs); set via env")
    ENV: str = "dev"

    HUB_CATEGORIES: dict[str, tuple[str, str]] = {
        "ai-tools": ("AI & Crypto", "AI & Crypto Tools — Free Online Predictors & Calculators"),
        "image-tools": ("Image Processing", "Free Online Image Tools — Background Remover, Compressor & Converter"),
        "calculators": ("Calculators", "Free Online Calculators — Math, Finance & Life Calculators"),
        "developer-tools": ("Developer & SEO", "Free Developer & SEO Tools — Schema, Sitemap & Code Generators"),
        "business-tools": ("Business & Operations", "Free Business Tools — Invoice, Orders & Finance Calculators"),
        "productivity-tools": (
            "Productivity & Utilities",
            "Free PDF & Productivity Tools — Converter, Password & Trackers",
        ),
        # Legacy alias: /pdf-tools 301s to /productivity-tools (kept for backlinks).
        "pdf-tools": ("Productivity & Utilities", "Free PDF & Productivity Tools — Converter, Password & Trackers"),
    }

    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @property
    def templates_dir(self) -> str:
        return os.path.join(self.base_dir, "templates")

    @property
    def static_dir(self) -> str:
        return os.path.join(self.base_dir, "static")

    @property
    def is_prod(self) -> bool:
        return (self.ENV or "").strip().lower() in ("prod", "production")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS:
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        base = [
            "https://www.storybrainai.com",
            "https://storybrainai.com",
        ]
        # Localhost origins only for non-prod (dev/test) to avoid credentialed local fetch in prod.
        if not self.is_prod:
            base += [
                "http://localhost:8090",
                "http://127.0.0.1:8090",
            ]
        return base

    @model_validator(mode="after")
    def _fail_fast_on_wildcard_hosts(self):
        raw = (self.ALLOWED_HOSTS or "").strip()
        if raw:
            parts = [h.strip() for h in raw.split(",") if h.strip()]
            if any(h == "*" for h in parts):
                raise ValueError(
                    "ALLOWED_HOSTS set to '*' — this is insecure. "
                    "Specify actual domains/IPs in .env. "
                    "Example: ALLOWED_HOSTS=storybrainai.com,www.storybrainai.com"
                )
        return self

    @model_validator(mode="after")
    def _fail_fast_on_missing_secret(self):
        if self.is_prod and self.SECRET_KEY in ("", "change-me"):
            raise ValueError(
                "SECRET_KEY must be set to a strong value when ENV==prod. "
                "Set SECRET_KEY in .env to a long random string."
            )
        return self

    @model_validator(mode="after")
    def _fail_fast_on_prod_hosts(self):
        if self.is_prod and not (self.ALLOWED_HOSTS or "").strip():
            raise ValueError(
                "ALLOWED_HOSTS must be set when ENV==prod. "
                "Example: ALLOWED_HOSTS=storybrainai.com,www.storybrainai.com"
            )
        return self

    @property
    def allowed_hosts_list(self) -> list[str]:
        if not self.ALLOWED_HOSTS.strip():
            return [
                "127.0.0.1",
                "localhost",
                "storybrainai.com",
                "www.storybrainai.com",
            ]
        result = [_normalize_host(h) for h in self.ALLOWED_HOSTS.split(",") if h.strip()]
        return [h for h in result if h]


settings = Settings()
