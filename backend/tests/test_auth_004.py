"""Black-box tests for AUTH-004 logout and authentication boundaries."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from django.db import connection
from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"
REFRESH_URL = "/api/v1/auth/refresh/"
ME_URL = "/api/v1/auth/me/"
PASSWORD = "StrongPass_123"


@pytest.fixture
def client():
    return Client()


def _json_response(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


@pytest.fixture
def auth_session(client):
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
    tokens = login.json()
    return {
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "password": PASSWORD,
    }


def _logout(client, access: str, refresh: str, payload: dict | None = None):
    return client.post(
        LOGOUT_URL,
        {"refresh": refresh} if payload is None else payload,
        HTTP_AUTHORIZATION=f"Bearer {access}",
        content_type="application/json",
    )


@pytest.mark.django_db
def test_logout_returns_204_blacklists_refresh_and_keeps_response_empty(
    client, auth_session
):
    response = _logout(client, auth_session["access"], auth_session["refresh"])

    assert response.status_code == 204
    assert response.content == b""
    assert auth_session["access"] not in response.content.decode()
    assert auth_session["refresh"] not in response.content.decode()
    assert auth_session["password"] not in response.content.decode()

    refresh_after_logout = Client().post(
        REFRESH_URL,
        {"refresh": auth_session["refresh"]},
        content_type="application/json",
    )
    assert refresh_after_logout.status_code == 401
    body = _json_response(refresh_after_logout)
    assert body["code"] == "INVALID_REFRESH_TOKEN"
    assert auth_session["refresh"] not in refresh_after_logout.content.decode()


@pytest.mark.django_db
def test_repeated_logout_is_idempotent_and_does_not_reveal_token_state(
    client, auth_session
):
    first = _logout(client, auth_session["access"], auth_session["refresh"])
    assert first.status_code == 204

    second = _logout(client, auth_session["access"], auth_session["refresh"])

    assert second.status_code == 204
    assert second.content == b""
    assert auth_session["refresh"] not in second.content.decode()


@pytest.mark.django_db
def test_expired_refresh_logout_is_idempotent_without_unhandled_error(
    client, auth_session
):
    expired = RefreshToken(auth_session["refresh"])
    expired["exp"] = int(time.time()) - 1
    expired_value = str(expired)

    response = _logout(client, auth_session["access"], expired_value)

    assert response.status_code == 204
    assert response.content == b""
    assert expired_value not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("authorization", "payload"),
    [
        (None, {"refresh": "not-a-jwt"}),
        ("Bearer not-a-jwt", {"refresh": "not-a-jwt"}),
        ("Bearer {access}", {"refresh": "not-a-jwt"}),
    ],
)
def test_missing_or_invalid_logout_credentials_return_safe_4xx(
    client, auth_session, authorization, payload
):
    header = None if authorization is None else authorization.format(**auth_session)
    request_headers = {} if header is None else {"HTTP_AUTHORIZATION": header}
    response = client.post(
        LOGOUT_URL,
        payload,
        content_type="application/json",
        **request_headers,
    )

    assert 400 <= response.status_code < 500
    assert auth_session["access"] not in response.content.decode()
    assert auth_session["refresh"] not in response.content.decode()
    assert auth_session["password"] not in response.content.decode()


@pytest.mark.django_db
def test_logout_requires_refresh_field_and_protected_me_requires_authentication(
    client, auth_session
):
    missing_refresh = _logout(
        client,
        auth_session["access"],
        auth_session["refresh"],
        payload={},
    )
    assert 400 <= missing_refresh.status_code < 500
    assert auth_session["refresh"] not in missing_refresh.content.decode()

    unauthenticated_me = client.get(ME_URL)
    assert unauthenticated_me.status_code == 401


@pytest.mark.django_db
def test_logout_does_not_turn_existing_access_into_token_or_sensitive_response(
    client, auth_session
):
    response = _logout(client, auth_session["access"], auth_session["refresh"])
    assert response.status_code == 204

    me_after_logout = client.get(
        ME_URL,
        HTTP_AUTHORIZATION=f"Bearer {auth_session['access']}",
    )
    assert me_after_logout.status_code in {200, 401}
    if me_after_logout.status_code == 200:
        assert set(me_after_logout.json()) == {"id", "username", "email"}
        assert auth_session["password"] not in me_after_logout.content.decode()
        assert auth_session["refresh"] not in me_after_logout.content.decode()


def _refresh_in_new_django_process(refresh: str) -> subprocess.CompletedProcess[str]:
    if shutil.which("uv") is None:
        pytest.skip("uv 不可用，无法执行独立 Django 进程持久化验证")

    configured_url = os.environ["DATABASE_URL"]
    parsed = urlsplit(configured_url)
    test_database_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            str(connection.settings_dict["NAME"]),
            parsed.query,
            parsed.fragment,
        )
    )
    probe = (
        "from django.test import Client; "
        f"r=Client().post('/api/v1/auth/refresh/', "
        f"{{'refresh': {json.dumps(refresh)}}}, content_type='application/json'); "
        "print('status=' + str(r.status_code)); "
        "print('content=' + r.content.decode())"
    )
    environment = os.environ.copy()
    environment["DATABASE_URL"] = test_database_url
    return subprocess.run(
        ["uv", "run", "--no-sync", "python", "manage.py", "shell", "-c", probe],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
def _register_and_login(client):
    username = f"cross{uuid.uuid4().hex[:12]}"
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
    return login.json()


@pytest.mark.django_db
def test_cross_user_access_and_refresh_pair_returns_safe_4xx_without_blacklisting_owner(
    client,
):
    owner = _register_and_login(client)
    other_user = _register_and_login(client)

    response = client.post(
        LOGOUT_URL,
        {"refresh": owner["refresh"]},
        HTTP_AUTHORIZATION=f"Bearer {other_user['access']}",
        content_type="application/json",
    )

    assert 400 <= response.status_code < 500
    assert owner["access"] not in response.content.decode()
    assert owner["refresh"] not in response.content.decode()

    owner_refresh = client.post(
        REFRESH_URL,
        {"refresh": owner["refresh"]},
        content_type="application/json",
    )
    assert owner_refresh.status_code == 200
@pytest.mark.django_db(transaction=True)
def test_logout_blacklist_persists_across_a_new_django_process(client, auth_session):
    logout = _logout(client, auth_session["access"], auth_session["refresh"])
    assert logout.status_code == 204

    restarted_process = _refresh_in_new_django_process(auth_session["refresh"])

    assert restarted_process.returncode == 0, (
        "独立 Django 进程无法启动公开 refresh 探针："
        f"stdout={restarted_process.stdout}\n"
        f"stderr={restarted_process.stderr}"
    )
    assert "status=401" in restarted_process.stdout
    assert "INVALID_REFRESH_TOKEN" in restarted_process.stdout
    assert auth_session["refresh"] not in restarted_process.stdout