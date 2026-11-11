"""Application configuration via Pydantic Settings (env file + defaults).

Wiring notes (kept trivial on purpose):
- ``LOG_LEVEL`` is consumed by ``app.core.log.setup_logging`` / gunicorn
  (``gunicorn_conf.py`` reads ``LOG_LEVEL`` env directly).
- ``CACHE_DEFAULT_TTL`` is the fallback TTL used by
  ``app.core.cache.CacheService`` when callers pass no explicit TTL.
"""

import hashlib
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
    INDEXNOW_KEY: str = Field(
        default="",
        description="IndexNow key (Bing/Yandex instant indexing); served at /<KEY>.txt, used by scripts/submit_indexnow.py",
    )
    STRIP_MARKETING_PARAMS: bool = Field(
        default=False,
        description="When true, CleanQueryMiddleware 301-strips utm_* and ad click parameters (gclid, fbclid). "
        "Keep false to preserve campaign and conversion attribution in Google Analytics and AdSense.",
    )
    STRICT_ORIGIN_CHECK: bool = Field(
        default=False,
        description="When true, header-less cross-origin writes (no Origin/Referer/Sec-Fetch-Site) are 403'd. "
        "Keep false if non-browser clients (curl, server-to-server) use the write APIs.",
    )

    SUPPORTED_LOCALES: tuple[str, ...] = ("en",)
    DEFAULT_LOCALE: str = "en"

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
                "ALLOWED_HOSTS must be set when ENV==prod. Example: ALLOWED_HOSTS=storybrainai.com,www.storybrainai.com"
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


class _FileHashCache:
    """Stat-cached SHA-256 prefix over one or more files on disk."""

    def __init__(self, paths: list[str]) -> None:
        self._paths = paths
        self._cached_sig: tuple[tuple[int, int] | None, ...] | None = None
        self._cached_digest: str = ""

    def digest(self) -> str:
        sigs: list[tuple[int, int] | None] = []
        for path in self._paths:
            try:
                st = os.stat(path)
                sigs.append((st.st_mtime_ns, st.st_size))
            except OSError:
                sigs.append(None)
        sig_tuple = tuple(sigs)
        if sig_tuple == self._cached_sig:
            return self._cached_digest
        if not any(sig_tuple):
            self._cached_digest = ""
            self._cached_sig = sig_tuple
            return ""
        hasher = hashlib.sha256()
        for path, sig in zip(self._paths, sig_tuple):
            if sig is None:
                continue
            try:
                with open(path, "rb") as f:
                    hasher.update(f.read())
            except OSError:
                pass
        digest = hasher.hexdigest()[:8]
        # Write digest before sig_tuple so concurrent readers never pair a fresh sig with a stale digest.
        self._cached_digest = digest
        self._cached_sig = sig_tuple
        return digest


class _DynamicAssetVersion:
    """Resolve asset cache-buster combining explicit APP_VERSION with bundle content hash."""

    def __init__(self, static_dir: str) -> None:
        self._static_dir = static_dir
        self._hash_cache = _FileHashCache([
            os.path.join(static_dir, "css", "app.css"),
            os.path.join(static_dir, "js", "app.js"),
        ])

    def _bundle_digest(self) -> str:
        return self._hash_cache.digest()

    def _resolve(self) -> str:
        explicit = os.getenv("APP_VERSION", "").strip()
        base = explicit if explicit else "dev"
        digest = self._bundle_digest()
        if digest:
            return f"{base}-{digest}"
        return base

    def __str__(self) -> str:
        return self._resolve()

    def __repr__(self) -> str:
        return self._resolve()


class _DynamicAppCssHref:
    """Resolve stylesheet href to content-hashed app.<hash8>.css when present on disk."""

    def __init__(self, static_dir: str, asset_version: _DynamicAssetVersion) -> None:
        self._static_dir = static_dir
        self._asset_version = asset_version
        self._hash_cache = _FileHashCache([os.path.join(static_dir, "css", "app.css")])

    def _resolve(self) -> str:
        digest = self._hash_cache.digest()
        if digest:
            hashed_name = f"app.{digest}.css"
            hashed_path = os.path.join(self._static_dir, "css", hashed_name)
            if os.path.isfile(hashed_path):
                return f"/static/css/{hashed_name}"
        return f"/static/css/app.css?v={self._asset_version}"

    def __str__(self) -> str:
        return self._resolve()

    def __repr__(self) -> str:
        return self._resolve()


APP_VERSION = _DynamicAssetVersion(settings.static_dir)
APP_CSS_HREF = _DynamicAppCssHref(settings.static_dir, APP_VERSION)
