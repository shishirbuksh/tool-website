from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403, F405

DEBUG = False

if ENV in ("prod", "production"):  # noqa: F405
    if (
        not SECRET_KEY  # noqa: F405
        or SECRET_KEY.startswith("django-insecure-")  # noqa: F405
        or SECRET_KEY == "change-me"  # noqa: F405
        or len(SECRET_KEY) < 32  # noqa: F405
    ):
        raise ImproperlyConfigured(
            "Production (ENV=prod) requires a strong SECRET_KEY (>=32 chars, not default/change-me)."
        )
    if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:  # noqa: F405
        raise ImproperlyConfigured(
            "Production (ENV=prod) requires explicit ALLOWED_HOSTS without wildcards."
        )

# Production security headers and cookie policies
SECURE_SSL_REDIRECT = False  # Handled at Caddy edge
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Custom middleware SecurityHeadersMiddleware handles HSTS, nosniff, CSP, X-Frame-Options,
# and origin checks natively.
SILENCED_SYSTEM_CHECKS = [
    "security.W001",  # Handled in SecurityHeadersMiddleware
    "security.W002",  # Handled in SecurityHeadersMiddleware
    "security.W003",  # API-driven & client-side tools with origin verification
]

