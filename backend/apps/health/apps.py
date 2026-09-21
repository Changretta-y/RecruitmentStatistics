from django.apps import AppConfig


class HealthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.apps.health"

    def ready(self):
        from . import checks  # noqa: F401
