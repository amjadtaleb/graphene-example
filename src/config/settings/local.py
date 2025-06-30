# In this file, we can override the settings from base.py for local development.
from .base import *

# For now, it's the same as base, but we can add things like DEBUG = True here.
DEBUG = True


# MIDDLEWARE.insert(
#     0,
#     "kolo.middleware.KoloMiddleware",
# )

INSTALLED_APPS.append("django_extensions")

MIDDLEWARE.insert(0, "kolo.middleware.KoloMiddleware")