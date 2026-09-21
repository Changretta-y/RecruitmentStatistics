"""Deployment checks for required secrets and unsafe production switches."""

from __future__ import annotations

import os

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def security_configuration_check(app_configs, **kwargs):
    errors = []
    if not settings.SECRET_KEY:
        errors.append(
            Error(
                "DJANGO_SECRET_KEY (or SECRET_KEY) is required and must not be empty.",
                id="security.E100",
            )
        )
    if not getattr(settings, "DATABASE_URL", ""):
        errors.append(
            Error(
                "DATABASE_URL is required; configure a PostgreSQL connection URL.",
                id="security.E101",
            )
        )
    if settings.DEBUG:
        errors.append(
            Error(
                "DJANGO_DEBUG=true is not allowed for deployment.",
                id="security.E102",
            )
        )
    raw_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    if "*" in getattr(settings, "CORS_ALLOWED_ORIGINS", ()) or "*" in raw_origins:
        errors.append(
            Error(
                "CORS_ALLOWED_ORIGINS must list explicit origins and must not contain '*'.",
                id="security.E103",
            )
        )
    return errors
