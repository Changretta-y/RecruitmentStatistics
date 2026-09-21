"""Black-box tests for APP-007 application deletion and ownership boundaries."""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
PASSWORD = "StrongPass_123"
MISSING_ID = 987654321


@pytest.fixture
def client():
    return Client()


def _register(client, prefix):
    username = f"{prefix}{uuid.uuid4().hex[:12]}"
    credentials = {
        "username": username,
        "email": f"{username}@example.com",
        "password": PASSWORD,
    }
    response = client.post(
        REGISTER_URL,
        {**credentials, "password_confirm": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 201
    return credentials


def _login(client, credentials):
    response = client.post(LOGIN_URL, credentials, content_type="application/json")
    assert response.status_code == 200
    user = get_user_model().objects.get(username=credentials["username"])
    return {"access": response.json()["access"], "user": user}


@pytest.fixture
def owner(client):
    return _login(client, _register(client, "app007owner"))


@pytest.fixture
def other_user(client):
    return _login(client, _register(client, "app007other"))


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _create(client, session):
    response = client.post(
        APPLICATIONS_URL,
        {
            "company_name": "待删除科技",
            "position_name": "后端工程师",
            "application_status": "in_progress",
            "application_time": "2026-01-10T09:00:00+08:00",
            "notes": "APP-007 test record",
        },
        content_type="application/json",
        **_headers(session),
    )
    assert response.status_code == 201
    return response.json()


def _delete(client, session, application_id):
    return client.delete(
        f"{APPLICATIONS_URL}{application_id}/",
        **_headers(session),
    )


def _error_signature(response):
    assert response.status_code == 404
    body = _json(response)
    return response.status_code, body.get("code")


@pytest.mark.django_db
def test_owner_delete_returns_204_and_record_disappears_from_list_and_detail(
    client, owner
):
    created = _create(client, owner)

    response = _delete(client, owner, created["id"])

    assert response.status_code == 204
    assert response.content == b""
    list_response = client.get(APPLICATIONS_URL, **_headers(owner))
    assert list_response.status_code == 200
    assert created["id"] not in [item["id"] for item in _json(list_response)["results"]]
    detail_response = client.get(
        f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner)
    )
    assert _error_signature(detail_response) == (404, "NOT_FOUND")


@pytest.mark.django_db
def test_cross_user_delete_returns_same_404_as_missing_and_does_not_change_target(
    client, owner, other_user
):
    created = _create(client, owner)

    cross_user = _delete(client, other_user, created["id"])
    missing = _delete(client, other_user, MISSING_ID)

    assert _error_signature(cross_user) == _error_signature(missing)
    unchanged = client.get(
        f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner)
    )
    assert unchanged.status_code == 200
    assert _json(unchanged)["id"] == created["id"]
    assert _json(unchanged)["notes"] == created["notes"]


@pytest.mark.django_db
def test_repeated_delete_is_404_and_matches_missing_id_behavior(client, owner):
    created = _create(client, owner)

    first = _delete(client, owner, created["id"])
    repeated = _delete(client, owner, created["id"])
    missing = _delete(client, owner, MISSING_ID)

    assert first.status_code == 204
    assert _error_signature(repeated) == _error_signature(missing)


@pytest.mark.django_db
def test_unauthenticated_delete_returns_401_and_keeps_record_visible(client, owner):
    created = _create(client, owner)

    response = client.delete(f"{APPLICATIONS_URL}{created['id']}/")

    assert response.status_code == 401
    visible = client.get(
        f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner)
    )
    assert visible.status_code == 200
    assert _json(visible)["id"] == created["id"]
