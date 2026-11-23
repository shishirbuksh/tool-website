from .base import *  # noqa: F403

DEBUG = False

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

