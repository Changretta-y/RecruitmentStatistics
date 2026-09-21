"""Black-box tests for APP-004 application pagination."""

from __future__ import annotations

from math import ceil
from urllib.parse import parse_qs, urlparse
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
PASSWORD = "StrongPass_123"
OWN_COUNT = 21
OTHER_COUNT = 2


@pytest.fixture
def client():
    return Client()


def _register(client, username_prefix: str):
    username = f"{username_prefix}{uuid.uuid4().hex[:12]}"
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
def populated_sessions(client):
    owner = _login(client, _register(client, "app004owner"))
    other = _login(client, _register(client, "app004other"))
    for index in range(OWN_COUNT):
        response = client.post(
            APPLICATIONS_URL,
            {
                "company_name": f"本人公司{index:02d}",
                "position_name": "后端工程师",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {owner['access']}",
        )
        assert response.status_code == 201
    for index in range(OTHER_COUNT):
        response = client.post(
            APPLICATIONS_URL,
            {
                "company_name": f"他人公司{index:02d}",
                "position_name": "前端工程师",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {other['access']}",
        )
        assert response.status_code == 201
    return owner, other


def _get(client, owner, query=""):
    return client.get(
        f"{APPLICATIONS_URL}{query}",
        HTTP_AUTHORIZATION=f"Bearer {owner['access']}",
    )


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _assert_page(body, *, page, page_size, result_count, total_pages):
    assert {"count", "page", "page_size", "total_pages", "next", "previous", "results"} <= set(body)
    assert body["count"] == OWN_COUNT
    assert body["page"] == page
    assert body["page_size"] == page_size
    assert body["total_pages"] == total_pages
    assert len(body["results"]) == result_count
    if body["results"]:
        assert all(item["user"] == body["results"][0]["user"] for item in body["results"])


@pytest.mark.django_db
def test_default_page_is_one_and_page_size_is_twenty(populated_sessions, client):
    owner, _other = populated_sessions

    response = _get(client, owner)

    assert response.status_code == 200
    body = _json(response)
    _assert_page(
        body,
        page=1,
        page_size=20,
        result_count=20,
        total_pages=2,
    )
    assert body["next"] is not None
    assert body["previous"] is None
    assert all(item["user"] == owner["user"].id for item in body["results"])


@pytest.mark.django_db
@pytest.mark.parametrize("page_size", [10, 20, 50, 100])
def test_allowed_page_sizes_are_honored(populated_sessions, client, page_size):
    owner, _other = populated_sessions

    response = _get(client, owner, f"?page_size={page_size}")

    assert response.status_code == 200
    body = _json(response)
    _assert_page(
        body,
        page=1,
        page_size=page_size,
        result_count=min(page_size, OWN_COUNT),
        total_pages=ceil(OWN_COUNT / page_size),
    )
    assert all(item["user"] == owner["user"].id for item in body["results"])


@pytest.mark.django_db
@pytest.mark.parametrize("page_size", ["0", "1", "101", "-1", "abc", "20.5"])
def test_invalid_page_size_returns_structured_400(page_size, populated_sessions, client):
    owner, _other = populated_sessions

    response = _get(client, owner, f"?page_size={page_size}")

    assert response.status_code == 400
    body = _json(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert "page_size" in body["details"]


@pytest.mark.django_db
def test_out_of_range_page_has_fixed_empty_result_behavior_and_preserves_count(
    populated_sessions, client
):
    owner, _other = populated_sessions

    response = _get(client, owner, "?page=4&page_size=10")

    assert response.status_code in {200, 404}
    if response.status_code == 200:
        body = _json(response)
        _assert_page(body, page=4, page_size=10, result_count=0, total_pages=3)
        assert body["results"] == []


@pytest.mark.django_db
def test_next_previous_preserve_page_size_and_never_cross_user_boundary(
    populated_sessions, client
):
    owner, _other = populated_sessions

    first = _json(_get(client, owner, "?page=1&page_size=10"))
    second = _json(_get(client, owner, "?page=2&page_size=10"))
    third = _json(_get(client, owner, "?page=3&page_size=10"))

    assert first["next"] is not None
    assert first["previous"] is None
    assert second["next"] is not None
    assert second["previous"] is not None
    assert third["next"] is None
    assert third["previous"] is not None

    first_next = parse_qs(urlparse(first["next"]).query)
    second_next = parse_qs(urlparse(second["next"]).query)
    second_previous = parse_qs(urlparse(second["previous"]).query)
    third_previous = parse_qs(urlparse(third["previous"]).query)
    assert first_next["page_size"] == ["10"]
    assert first_next["page"] == ["2"]
    assert second_next["page_size"] == ["10"]
    assert second_previous["page_size"] == ["10"]
    assert third_previous["page_size"] == ["10"]

    for body in (first, second, third):
        assert all(item["user"] == owner["user"].id for item in body["results"])
        assert body["count"] == OWN_COUNT
