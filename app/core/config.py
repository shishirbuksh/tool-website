import functools
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
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    CORS_ORIGINS: str = ""

    @functools.cached_property
    def BASE_DIR(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @functools.cached_property
    def TEMPLATES_DIR(self) -> str:
        return os.path.join(self.BASE_DIR, "templates")

    @functools.cached_property
    def STATIC_DIR(self) -> str:
        return os.path.join(self.BASE_DIR, "static")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS:
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return [
            "https://www.storybrainai.com",
            "https://storybrainai.com",
            "http://localhost:8000",
        ]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]


settings = Settings()
