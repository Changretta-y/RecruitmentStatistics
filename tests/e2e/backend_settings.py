"""E2E-only settings overlay; production settings remain untouched."""

from config.settings import *  # noqa: F401,F403

STATIC_URL = "/static/"
