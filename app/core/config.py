"""Application configuration via Pydantic Settings (env file + defaults)."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "Multi-Tool Website"
    HOST: str = "0.0.0.0"
    PORT: int = 8090
    LOG_LEVEL: str = "info"
    WORKERS: int = 0
    TIMEOUT: int = 120
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

    HUB_CATEGORIES: dict[str, tuple[str, str]] = {
        "ai-tools": ("AI & Crypto", "AI & Crypto Tools — Free Online Predictors & Calculators"),
        "image-tools": ("Image Processing", "Free Online Image Tools — Background Remover, Compressor & Converter"),
        "calculators": ("Calculators", "Free Online Calculators — Math, Finance & Life Calculators"),
        "developer-tools": ("Developer & SEO", "Free Developer & SEO Tools — Schema, Sitemap & Code Generators"),
        "business-tools": ("Business & Operations", "Free Business Tools — Invoice, Orders & Finance Calculators"),
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
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS:
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return [
            "https://www.storybrainai.com",
            "https://storybrainai.com",
            "http://localhost:8090",
            "http://127.0.0.1:8090",
        ]

    @property
    def allowed_hosts_list(self) -> list[str]:
        if not self.ALLOWED_HOSTS.strip():
            return [
                "127.0.0.1",
                "localhost",
                "storybrainai.com",
                "www.storybrainai.com",
            ]
        result = [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]
        if any(h == "*" for h in result):
            raise ValueError(
                "ALLOWED_HOSTS set to '*' — this is insecure. "
                "Specify actual domains/IPs in .env. "
                "Example: ALLOWED_HOSTS=storybrainai.com,www.storybrainai.com"
            )
        return result


settings = Settings()
