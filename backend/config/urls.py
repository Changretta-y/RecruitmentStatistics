"""Public URL configuration for the backend service."""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path("", include("backend.apps.mcp.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/v1/", include("backend.apps.health.urls")),
    path("api/v1/auth/", include("backend.apps.accounts.urls")),
    path("api/v1/", include("backend.apps.notifications.urls")),
    path("api/v1/", include("backend.apps.calendar_events.urls")),
    path("api/v1/companies/", include("backend.apps.applications.company_urls")),
    path("api/v1/applications/", include("backend.apps.applications.urls")),
    path("api/v1/sharing/", include("backend.apps.sharing.urls")),
]
