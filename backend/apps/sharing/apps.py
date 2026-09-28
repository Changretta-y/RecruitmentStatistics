from django.apps import AppConfig


class SharingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.apps.sharing"

    def ready(self):
        from . import checks, signals  # noqa: F401
