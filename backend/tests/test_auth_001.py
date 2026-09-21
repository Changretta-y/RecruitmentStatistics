"""Black-box tests for the AUTH-001 registration contract."""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
REGISTER_PASSWORD = "StrongPass_123"


def _payload(**overrides: str) -> dict[str, str]:
    username = f"auth{uuid.uuid4().hex[:12]}"
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": REGISTER_PASSWORD,
        "password_confirm": REGISTER_PASSWORD,
    }
    payload.update(overrides)
    return payload


def _json_response(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


@pytest.mark.django_db
def test_register_persists_user_with_hashed_password_and_safe_response():
    client = Client()
    payload = _payload()

    response = client.post(REGISTER_URL, payload, content_type="application/json")

    assert response.status_code == 201
    body = _json_response(response)
    assert set(body) == {"id", "username", "email", "date_joined"}
    assert body["username"] == payload["username"]
    assert body["email"] == payload["email"]
    assert REGISTER_PASSWORD not in response.content.decode()

    user = get_user_model().objects.get(username=payload["username"])
    assert user.check_password(REGISTER_PASSWORD)
    assert user.password != REGISTER_PASSWORD
    assert user.password not in response.content.decode()


@pytest.mark.django_db
def test_register_is_available_without_authentication():
    client = Client()
    response = client.post(
        REGISTER_URL,
        _payload(),
        content_type="application/json",
    )

    assert response.status_code == 201


@pytest.mark.django_db
def test_duplicate_username_returns_explicit_conflict_code():
    client = Client()
    payload = _payload()
    first = client.post(REGISTER_URL, payload, content_type="application/json")
    assert first.status_code == 201

    duplicate = client.post(REGISTER_URL, payload, content_type="application/json")

    assert duplicate.status_code == 409
    body = _json_response(duplicate)
    assert body["code"] == "USERNAME_ALREADY_EXISTS"


@pytest.mark.django_db
def test_password_mismatch_returns_explicit_error_code():
    client = Client()

    response = client.post(
        REGISTER_URL,
        _payload(password_confirm="DifferentPass_123"),
        content_type="application/json",
    )

    assert response.status_code == 400
    body = _json_response(response)
    assert body["code"] == "PASSWORDS_DO_NOT_MATCH"


@pytest.mark.django_db
def test_weak_password_returns_explicit_error_code():
    client = Client()

    response = client.post(
        REGISTER_URL,
        _payload(password="password", password_confirm="password"),
        content_type="application/json",
    )

    assert response.status_code == 400
    body = _json_response(response)
    assert body["code"] == "WEAK_PASSWORD"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"username": "ab"}, "username"),
        ({"email": "not-an-email"}, "email"),
    ],
)
def test_invalid_registration_fields_return_structured_validation_error(
    overrides: dict[str, str], field: str
):
    client = Client()

    response = client.post(
        REGISTER_URL,
        _payload(**overrides),
        content_type="application/json",
    )

    assert response.status_code == 400
    body = _json_response(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert isinstance(body["details"], dict)
    assert body["details"].get(field)
