from django.urls import path

from .views import NotificationSettingsView, VerificationRequestView, VerifyAddressView


urlpatterns = [
    path("notification-settings/", NotificationSettingsView.as_view(), name="notification-settings"),
    path(
        "notification-settings/verification/",
        VerificationRequestView.as_view(),
        name="notification-verification-request",
    ),
    path(
        "notification-settings/verify/",
        VerifyAddressView.as_view(),
        name="notification-verification-confirm",
    ),
]
