"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

from .opentelemetry import setup_telemetry

# Initialize OpenTelemetry before the application is loaded
setup_telemetry()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_asgi_application()

# Wrap the application with the OpenTelemetry middleware
application = OpenTelemetryMiddleware(application)
