"""Base Django settings for StoryBrain AI.

Following django-patterns and django-expert architecture guidelines:
- Thin views, decoupled domain apps
- Environment variable separation via django-environ
- Jinja2 template engine supporting all tool macros & rich schemas
- Production-grade security headers & middleware stack
"""

from __future__ import annotations

import os
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = str(BASE_DIR / "templates")
templates_dir = TEMPLATES_DIR
STATIC_DIR = str(BASE_DIR / "static")
static_dir = STATIC_DIR

env = environ.Env()
# Read .env file if it exists
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# Project Identification
PROJECT_NAME = env.str("PROJECT_NAME", default="StoryBrain AI")
SITE_URL = env.str("SITE_URL", default="https://www.storybrainai.com").rstrip("/")
APP_VERSION = env.str("APP_VERSION", default="1.0.1")

# Security
SECRET_KEY = env.str("SECRET_KEY", default="django-insecure-storybrain-secret-key-change-in-production")
ENV = env.str("ENV", default="dev").lower()
DEBUG = env.bool("DEBUG", default=(ENV != "prod" and ENV != "production"))

# Hosts & Networking
raw_allowed = env.str("ALLOWED_HOSTS", default="")
if raw_allowed.strip():
    ALLOWED_HOSTS = [h.strip() for h in raw_allowed.split(",") if h.strip()]
else:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost", "storybrainai.com", "www.storybrainai.com"]

CORS_ORIGINS = env.list("CORS_ORIGINS", default=["https://www.storybrainai.com", "https://storybrainai.com"])

# Application definition
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "apps.core",
    "apps.catalog",
    "apps.blog",
    "apps.seo",
    "apps.tools_api",
    "apps.analytics",
]

MIDDLEWARE = [
    "apps.core.middleware.TrustedHostCheckMiddleware",
    "apps.core.middleware.RequestIDMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
    "apps.core.middleware.CanonicalHostMiddleware",
    "apps.core.middleware.CaseSensitiveRedirectMiddleware",
    "apps.core.middleware.TrailingSlashRedirectMiddleware",
    "apps.core.middleware.CleanQueryMiddleware",
    "apps.core.middleware.OriginCheckMiddleware",
    "apps.core.middleware.RateLimitMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "apps.core.middleware.ConditionalGetMiddleware",
]

ROOT_URLCONF = "config.urls"

# Jinja2 Environment configuration
def jinja2_environment(**options):
    from jinja2 import Environment
    from apps.core.config import _DynamicAppCssHref, _DynamicAssetVersion
    from apps.core.icons import lucide_icon
    from apps.core.sanitize import enhance_tables, sanitize_html
    from datetime import datetime, UTC

    asset_version = _DynamicAssetVersion(STATIC_DIR)
    app_css_href = _DynamicAppCssHref(STATIC_DIR, asset_version)

    env = Environment(**options)
    env.globals.update({
        "lucide_icon": lucide_icon,
        "today": lambda: datetime.now(UTC).strftime("%Y-%m-%d"),
        "current_year": lambda: datetime.now(UTC).year,
        "SITE_URL": SITE_URL,
        "site_url": SITE_URL,
        "app_version": asset_version,
        "app_css_href": app_css_href,
        "adsense_blog_slot_id": env_var_slot("ADSENSE_BLOG_SLOT_ID"),
        "adsense_tool_slot_id": env_var_slot("ADSENSE_TOOL_SLOT_ID"),
    })
    env.filters["sanitize"] = sanitize_html
    env.filters["tables"] = enhance_tables
    return env


def env_var_slot(name: str) -> str:
    return os.environ.get(name, "").strip()


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [str(BASE_DIR / "templates")],
        "APP_DIRS": False,
        "OPTIONS": {
            "environment": "config.settings.base.jinja2_environment",
            "autoescape": True,
        },
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database (lightweight default SQLite for analytics, or WAL-managed storage)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "var" / "data" / "analytics.db",
    }
}

# Cache Configuration
REDIS_URL = env.str("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "storybrain-locmem-cache",
            "TIMEOUT": 300,
        }
    }

# Internationalization
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATICFILES_DIRS = [str(BASE_DIR / "static")]
STATIC_ROOT = str(BASE_DIR / "var" / "static_collected")

# File Upload Limits
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024  # 25 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

# Custom Project Configurations
IMAGE_MAX_SIZE = 10 * 1024 * 1024
PDF_MAX_SIZE = 5 * 1024 * 1024
INDEXNOW_KEY = env.str("INDEXNOW_KEY", default="")
CONTACT_EMAIL = env.str("CONTACT_EMAIL", default="")
SMTP_HOST = env.str("SMTP_HOST", default="localhost")
SMTP_PORT = env.int("SMTP_PORT", default=25)
SMTP_USER = env.str("SMTP_USER", default="")
SMTP_PASS = env.str("SMTP_PASS", default="")
STRIP_MARKETING_PARAMS = env.bool("STRIP_MARKETING_PARAMS", default=False)
ADSENSE_BLOG_SLOT_ID = env.str("ADSENSE_BLOG_SLOT_ID", default="")
ADSENSE_TOOL_SLOT_ID = env.str("ADSENSE_TOOL_SLOT_ID", default="")

# Hub categories mapping
HUB_CATEGORIES = {
    "ai-tools": ("AI & Crypto", "AI & Crypto Tools — Free Online Predictors & Calculators"),
    "image-tools": ("Image Processing", "Free Online Image Tools — Background Remover, Compressor & Converter"),
    "calculators": ("Calculators", "Free Online Calculators — Math, Finance & Life Calculators"),
    "developer-tools": ("Developer & SEO", "Free Developer & SEO Tools — Schema, Sitemap & Code Generators"),
    "business-tools": ("Business & Operations", "Free Business Tools — Invoice, Orders & Finance Calculators"),
    "productivity-tools": ("Productivity & Utilities", "Free PDF & Productivity Tools — Converter, Password & Trackers"),
    "student-tools": ("Calculators", "Student Hub — Fast Online Math, Exam & Attendance Tools"),
    "pdf-tools": ("Productivity & Utilities", "Free PDF & Productivity Tools — Converter, Password & Trackers"),
}
