"""Test URL adapter that delegates to the public production URL contract."""

try:
    from backend.config.urls import urlpatterns
except ModuleNotFoundError as exc:
    if exc.name not in {"backend", "backend.config", "backend.config.urls"}:
        raise
    urlpatterns = []