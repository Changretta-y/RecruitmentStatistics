"""Black-box tests for the AUTH-002 login and current-user contract."""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
ME_URL = "/api/v1/auth/me/"
PASSWORD = "StrongPass_123"


@pytest.fixture
def client():
    return Client()


def _credentials() -> dict[str, str]:
    username = f"auth{uuid.uuid4().hex[:12]}"
    return {
        "username": username,
        "email": f"{username}@example.com",
        "password": PASSWORD,
    }


def _json_response(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


@pytest.fixture
def registered_user(client):
    credentials = _credentials()
    response = client.post(
        REGISTER_URL,
        {**credentials, "password_confirm": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 201
    return credentials


@pytest.mark.django_db
def test_login_returns_valid_tokens_expiry_configuration_and_safe_user(
    client, registered_user
):
    response = client.post(LOGIN_URL, registered_user, content_type="application/json")

    assert response.status_code == 200
    body = _json_response(response)
    assert set(body) == {
        "access",
        "refresh",
        "access_expires_in",
        "refresh_expires_in",
        "user",
    }
    assert body["access_expires_in"] == 1800
    assert body["refresh_expires_in"] == 604800
    assert set(body["user"]) == {"id", "username", "email"}
    assert body["user"]["username"] == registered_user["username"]
    assert body["user"]["email"] == registered_user["email"]
    assert registered_user["password"] not in response.content.decode()

    user = get_user_model().objects.get(username=registered_user["username"])
    assert user.password not in response.content.decode()

    access = AccessToken(body["access"])
    refresh = RefreshToken(body["refresh"])
    assert access["token_type"] == "access"
    assert refresh["token_type"] == "refresh"
    assert int(access["exp"]) - int(access["iat"]) == 1800
    assert int(refresh["exp"]) - int(refresh["iat"]) == 604800


@pytest.mark.django_db
def test_access_token_returns_current_user_only_without_sensitive_fields(
    client, registered_user
):
    login = client.post(LOGIN_URL, registered_user, content_type="application/json")
    assert login.status_code == 200
    token = login.json()["access"]

    response = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {token}")

    assert response.status_code == 200
    body = _json_response(response)
    assert set(body) == {"id", "username", "email"}
    assert body["username"] == registered_user["username"]
    assert body["email"] == registered_user["email"]
    assert registered_user["password"] not in response.content.decode()

    user = get_user_model().objects.get(username=registered_user["username"])
    assert user.password not in response.content.decode()


@pytest.mark.django_db
def test_me_requires_authentication_and_rejects_refresh_token(client, registered_user):
    unauthenticated = client.get(ME_URL)
    assert unauthenticated.status_code == 401

    login = client.post(LOGIN_URL, registered_user, content_type="application/json")
    assert login.status_code == 200
    refresh_token = login.json()["refresh"]

    refresh_as_access = client.get(
        ME_URL,
        HTTP_AUTHORIZATION=f"Bearer {refresh_token}",
    )
    assert refresh_as_access.status_code == 401


@pytest.mark.django_db
def test_wrong_password_returns_uniform_invalid_credentials_error(
    client, registered_user
):
    response = client.post(
        LOGIN_URL,
        {"username": registered_user["username"], "password": "WrongPass_123"},
        content_type="application/json",
    )

    assert response.status_code == 401
    body = _json_response(response)
    assert body["code"] == "INVALID_CREDENTIALS"


@pytest.mark.django_db
def test_unknown_username_returns_uniform_invalid_credentials_error(client):
    response = client.post(
        LOGIN_URL,
        {"username": "missing-user-001", "password": PASSWORD},
        content_type="application/json",
    )

    assert response.status_code == 401
    body = _json_response(response)
    assert body["code"] == "INVALID_CREDENTIALS"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [{"password": PASSWORD}, {"username": "missing-password-001"}],
)
def test_missing_login_fields_return_structured_validation_error(client, payload):
    response = client.post(LOGIN_URL, payload, content_type="application/json")

    assert response.status_code == 400
    body = _json_response(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert isinstance(body["details"], dict)
