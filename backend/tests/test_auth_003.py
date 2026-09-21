"""Black-box tests for AUTH-003 refresh-token rotation and expiry."""

from __future__ import annotations

import time
import uuid

import pytest
from django.test import Client
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
ME_URL = "/api/v1/auth/me/"
PASSWORD = "StrongPass_123"
ACCESS_LIFETIME = 1800
REFRESH_LIFETIME = 604800


@pytest.fixture
def client():
    return Client()


def _json_response(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


@pytest.fixture
def token_session(client):
    username = f"auth{uuid.uuid4().hex[:12]}"
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
    login_body = _json_response(login)
    assert login_body["refresh"]
    return login_body


@pytest.mark.django_db
def test_valid_refresh_rotates_tokens_and_new_access_reaches_me(client, token_session):
    old_access = token_session["access"]
    old_refresh = token_session["refresh"]

    response = client.post(
        REFRESH_URL,
        {"refresh": old_refresh},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = _json_response(response)
    assert set(body) == {
        "access",
        "refresh",
        "access_expires_in",
        "refresh_expires_in",
    }
    assert body["access"] != old_access
    assert body["refresh"] != old_refresh
    assert body["access_expires_in"] == ACCESS_LIFETIME
    assert body["refresh_expires_in"] == REFRESH_LIFETIME

    access = AccessToken(body["access"])
    refresh = RefreshToken(body["refresh"])
    assert access["token_type"] == "access"
    assert refresh["token_type"] == "refresh"
    assert int(access["exp"]) - int(access["iat"]) == ACCESS_LIFETIME

    me = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {body['access']}")
    assert me.status_code == 200
    assert set(me.json()) == {"id", "username", "email"}


@pytest.mark.django_db
def test_rotated_refresh_cannot_be_replayed_and_error_does_not_echo_token(
    client, token_session
):
    old_refresh = token_session["refresh"]
    first = client.post(
        REFRESH_URL,
        {"refresh": old_refresh},
        content_type="application/json",
    )
    assert first.status_code == 200

    replay = client.post(
        REFRESH_URL,
        {"refresh": old_refresh},
        content_type="application/json",
    )

    assert replay.status_code == 401
    body = _json_response(replay)
    assert body["code"] == "INVALID_REFRESH_TOKEN"
    assert old_refresh not in replay.content.decode()


@pytest.mark.django_db
def test_rotated_refresh_keeps_original_seven_day_absolute_deadline(
    client, token_session
):
    original = RefreshToken(token_session["refresh"])
    original_exp = int(original["exp"])
    assert original_exp - int(original["iat"]) == REFRESH_LIFETIME

    response = client.post(
        REFRESH_URL,
        {"refresh": token_session["refresh"]},
        content_type="application/json",
    )
    assert response.status_code == 200

    rotated = RefreshToken(response.json()["refresh"])
    assert int(rotated["exp"]) <= original_exp
    assert int(rotated["exp"]) - int(rotated["iat"]) <= REFRESH_LIFETIME


@pytest.mark.django_db
@pytest.mark.parametrize(
    "refresh_value",
    ["not-a-jwt", ""],
)
def test_invalid_refresh_values_return_401_without_token_leak(client, refresh_value):
    response = client.post(
        REFRESH_URL,
        {"refresh": refresh_value},
        content_type="application/json",
    )

    assert response.status_code == 401
    body = _json_response(response)
    assert body["code"] == "INVALID_REFRESH_TOKEN"
    if refresh_value:
        assert refresh_value not in response.content.decode()


@pytest.mark.django_db
def test_expired_refresh_token_returns_401_without_token_leak(client, token_session):
    expired = RefreshToken(token_session["refresh"])
    expired["exp"] = int(time.time()) - 1
    expired_value = str(expired)

    response = client.post(
        REFRESH_URL,
        {"refresh": expired_value},
        content_type="application/json",
    )

    assert response.status_code == 401
    body = _json_response(response)
    assert body["code"] == "INVALID_REFRESH_TOKEN"
    assert expired_value not in response.content.decode()


@pytest.mark.django_db
def test_access_token_cannot_be_used_as_refresh_token(client, token_session):
    response = client.post(
        REFRESH_URL,
        {"refresh": token_session["access"]},
        content_type="application/json",
    )

    assert response.status_code == 401
    body = _json_response(response)
    assert body["code"] == "INVALID_REFRESH_TOKEN"
