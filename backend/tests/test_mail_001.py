"""Black-box tests for the MAIL-001 notification settings API contract."""

from __future__ import annotations

import re
import uuid
from datetime import timedelta
from urllib.parse import unquote

import pytest
from django.core.mail.backends.base import BaseEmailBackend
from django.test import Client, override_settings
from django.utils import timezone


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
SETTINGS_URL = "/api/v1/notification-settings/"
REQUEST_VERIFICATION_URL = f"{SETTINGS_URL}verification/"
VERIFY_URL = f"{SETTINGS_URL}verify/"
PASSWORD = "StrongPass_123"


class FailingEmailBackend(BaseEmailBackend):
    """A test-only SMTP substitute that deterministically refuses a message."""

    def send_messages(self, email_messages):
        raise OSError("test mail transport unavailable")


@pytest.fixture
def client():
    return Client()


def _register_and_login(client, prefix="mail001"):
    username = f"{prefix}{uuid.uuid4().hex[:12]}"
    credentials = {
        "username": username,
        "email": f"{username}@example.com",
        "password": PASSWORD,
    }
    registered = client.post(
        REGISTER_URL,
        {**credentials, "password_confirm": PASSWORD},
        content_type="application/json",
    )
    assert registered.status_code == 201
    login = client.post(LOGIN_URL, credentials, content_type="application/json")
    assert login.status_code == 200
    return {"access": login.json()["access"], "username": username}


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _configure_pending_address(client, session, email="candidate@example.com"):
    response = client.patch(
        SETTINGS_URL,
        {"recipient_email": email, "daily_time": "08:30", "enabled": False},
        content_type="application/json",
        **_headers(session),
    )
    assert response.status_code == 200
    return _json(response)


def _token_from_verification_email():
    from django.core import mail

    assert mail.outbox, "verification request did not produce a captured email"
    body = mail.outbox[-1].body
    match = re.search(r"[?&]token=([^&\s\"'<>]+)", body)
    assert match, "captured verification email did not expose its public link token"
    return unquote(match.group(1))


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_settings_get_returns_safe_defaults_and_patch_persists_only_own_values(client):
    owner = _register_and_login(client)
    other = _register_and_login(client, "mail001other")

    initial = client.get(SETTINGS_URL, **_headers(owner))
    assert initial.status_code == 200
    body = _json(initial)
    assert body["recipient_email"] in {None, ""}
    assert body["daily_time"] in {None, ""}
    assert body["enabled"] is False
    assert body["verified"] is False
    assert body["timezone"] == "Asia/Shanghai"
    assert body["last_delivery"] is None
    assert not any(key in body for key in ("token", "verification_token", "smtp_password"))

    updated = client.patch(
        SETTINGS_URL,
        {"recipient_email": "owner@example.com", "daily_time": "07:45"},
        content_type="application/json",
        **_headers(owner),
    )
    assert updated.status_code == 200
    owner_settings = _json(updated)
    assert owner_settings["recipient_email"] == "owner@example.com"
    assert owner_settings["daily_time"] == "07:45"
    assert owner_settings["enabled"] is False
    assert owner_settings["verified"] is False

    other_body = _json(client.get(SETTINGS_URL, **_headers(other)))
    assert other_body["recipient_email"] in {None, ""}
    assert other_body["daily_time"] in {None, ""}
    assert other_body["enabled"] is False

    changed = client.patch(
        SETTINGS_URL,
        {"daily_time": "09:10"},
        content_type="application/json",
        **_headers(owner),
    )
    assert changed.status_code == 200
    assert _json(client.get(SETTINGS_URL, **_headers(owner)))["daily_time"] == "09:10"


@pytest.mark.django_db
def test_notification_endpoints_require_authentication(client):
    responses = [
        client.get(SETTINGS_URL),
        client.patch(SETTINGS_URL, {"enabled": False}, content_type="application/json"),
        client.post(REQUEST_VERIFICATION_URL, {}, content_type="application/json"),
        client.post(VERIFY_URL, {"token": "opaque"}, content_type="application/json"),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401, 401]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_invalid_settings_and_enable_before_email_verification_are_rejected(client):
    session = _register_and_login(client)
    invalid_email = client.patch(
        SETTINGS_URL,
        {"recipient_email": "not-an-email"},
        content_type="application/json",
        **_headers(session),
    )
    assert invalid_email.status_code == 400
    assert _json(invalid_email)["code"] == "VALIDATION_ERROR"
    assert "recipient_email" in _json(invalid_email)["details"]

    invalid_time = client.patch(
        SETTINGS_URL,
        {"daily_time": "25:61"},
        content_type="application/json",
        **_headers(session),
    )
    assert invalid_time.status_code == 400
    assert "daily_time" in _json(invalid_time)["details"]

    enabled_without_verified_address = client.patch(
        SETTINGS_URL,
        {"recipient_email": "pending@example.com", "daily_time": "08:00", "enabled": True},
        content_type="application/json",
        **_headers(session),
    )
    assert enabled_without_verified_address.status_code == 400
    assert _json(enabled_without_verified_address)["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_verification_token_is_sent_once_consumed_and_not_returned_by_api(client):
    session = _register_and_login(client)
    _configure_pending_address(client, session, "verify@example.com")

    requested = client.post(
        REQUEST_VERIFICATION_URL,
        {},
        content_type="application/json",
        **_headers(session),
    )
    assert requested.status_code == 202
    token = _token_from_verification_email()
    assert token not in requested.content.decode()

    verified = client.post(
        VERIFY_URL,
        {"token": token},
        content_type="application/json",
        **_headers(session),
    )
    assert verified.status_code == 200
    settings = _json(client.get(SETTINGS_URL, **_headers(session)))
    assert settings["recipient_email"] == "verify@example.com"
    assert settings["verified"] is True
    assert settings["enabled"] is False
    assert token not in verified.content.decode()
    assert token not in str(settings)

    enabled = client.patch(
        SETTINGS_URL,
        {"enabled": True},
        content_type="application/json",
        **_headers(session),
    )
    assert enabled.status_code == 200
    assert _json(enabled)["enabled"] is True

    changed_address = client.patch(
        SETTINGS_URL,
        {"recipient_email": "new-verify@example.com"},
        content_type="application/json",
        **_headers(session),
    )
    assert changed_address.status_code == 200
    changed_settings = _json(changed_address)
    assert changed_settings["recipient_email"] == "new-verify@example.com"
    assert changed_settings["verified"] is False
    assert changed_settings["enabled"] is False

    replay = client.post(
        VERIFY_URL,
        {"token": token},
        content_type="application/json",
        **_headers(session),
    )
    assert replay.status_code in {400, 404, 410}


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_verification_token_is_bound_to_user_and_current_recipient(client):
    owner = _register_and_login(client)
    other = _register_and_login(client, "mail001other")
    _configure_pending_address(client, owner, "owner-token@example.com")
    _configure_pending_address(client, other, "other-token@example.com")

    requested = client.post(
        REQUEST_VERIFICATION_URL,
        {},
        content_type="application/json",
        **_headers(owner),
    )
    assert requested.status_code == 202
    token = _token_from_verification_email()

    wrong_user = client.post(
        VERIFY_URL,
        {"token": token},
        content_type="application/json",
        **_headers(other),
    )
    assert wrong_user.status_code in {400, 404, 410}
    assert _json(client.get(SETTINGS_URL, **_headers(other)))["verified"] is False
    assert _json(client.get(SETTINGS_URL, **_headers(owner)))["verified"] is False

    changed = client.patch(
        SETTINGS_URL,
        {"recipient_email": "replacement@example.com"},
        content_type="application/json",
        **_headers(owner),
    )
    assert changed.status_code == 200
    stale_address = client.post(
        VERIFY_URL,
        {"token": token},
        content_type="application/json",
        **_headers(owner),
    )
    assert stale_address.status_code in {400, 404, 410}
    owner_settings = _json(client.get(SETTINGS_URL, **_headers(owner)))
    assert owner_settings["recipient_email"] == "replacement@example.com"
    assert owner_settings["verified"] is False


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_expired_verification_token_is_rejected(client, monkeypatch):
    session = _register_and_login(client)
    _configure_pending_address(client, session, "expired@example.com")

    request_time = timezone.now()
    monkeypatch.setattr("django.utils.timezone.now", lambda: request_time)
    requested = client.post(
        REQUEST_VERIFICATION_URL,
        {},
        content_type="application/json",
        **_headers(session),
    )
    assert requested.status_code == 202
    token = _token_from_verification_email()

    monkeypatch.setattr(
        "django.utils.timezone.now", lambda: request_time + timedelta(hours=25)
    )
    expired = client.post(
        VERIFY_URL,
        {"token": token},
        content_type="application/json",
        **_headers(session),
    )
    assert expired.status_code in {400, 404, 410}
    assert _json(client.get(SETTINGS_URL, **_headers(session)))["verified"] is False


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_verification_email_requests_are_limited_to_three_per_hour(client):
    session = _register_and_login(client)
    _configure_pending_address(client, session, "limited@example.com")

    responses = [
        client.post(
            REQUEST_VERIFICATION_URL,
            {},
            content_type="application/json",
            **_headers(session),
        )
        for _ in range(4)
    ]

    assert [response.status_code for response in responses] == [202, 202, 202, 429]
    from django.core import mail

    assert len(mail.outbox) == 3
    assert "token" not in responses[-1].content.decode().lower()


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="tests.test_mail_001.FailingEmailBackend",
    EMAIL_HOST="smtp.invalid.example",
    EMAIL_HOST_USER="platform-sender",
    EMAIL_HOST_PASSWORD="test-only-secret",
)
def test_smtp_failure_is_observable_and_does_not_verify_recipient(client):
    session = _register_and_login(client)
    _configure_pending_address(client, session, "retry@example.com")

    failed = client.post(
        REQUEST_VERIFICATION_URL,
        {},
        content_type="application/json",
        **_headers(session),
    )

    assert failed.status_code != 202
    assert "test-only-secret" not in failed.content.decode()
    settings = _json(client.get(SETTINGS_URL, **_headers(session)))
    assert settings["verified"] is False


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST="",
)
def test_missing_smtp_configuration_does_not_report_verification_as_sent(client):
    session = _register_and_login(client)
    _configure_pending_address(client, session, "smtp-missing@example.com")

    response = client.post(
        REQUEST_VERIFICATION_URL,
        {},
        content_type="application/json",
        **_headers(session),
    )

    assert response.status_code != 202
    settings = _json(client.get(SETTINGS_URL, **_headers(session)))
    assert settings["verified"] is False
