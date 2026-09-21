"""Minimal test-only Django bootstrap for the public health API contract."""

import sys
from pathlib import Path

import django
from django.conf import settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


if not settings.configured:
    settings.configure(
        SECRET_KEY="test-only-key",
        ROOT_URLCONF="backend.tests.test_urls",
        ALLOWED_HOSTS=["testserver"],
        INSTALLED_APPS=[],
        MIDDLEWARE=[],
        DEFAULT_CHARSET="utf-8",
    )

django.setup()