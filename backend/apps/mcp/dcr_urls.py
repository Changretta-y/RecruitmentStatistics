"""Namespaced OAuth Toolkit DCR routes used by the MCP issuer."""

from django.urls import path
from oauth2_provider.views import (
    DynamicClientRegistrationManagementView,
    DynamicClientRegistrationView,
)


app_name = "oauth2_provider"

urlpatterns = [
    path("register", DynamicClientRegistrationView.as_view(), name="dcr-register"),
    path(
        "register/<str:client_id>",
        DynamicClientRegistrationManagementView.as_view(),
        name="dcr-register-management",
    ),
]
