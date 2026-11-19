from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# In local development, enable immediate static and template reloading
TEMPLATES[0]["OPTIONS"]["auto_reload"] = True  # noqa: F405
