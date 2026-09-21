"""Black-box tests for APP-003 application list/detail isolation APIs."""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
PASSWORD = "StrongPass_123"
RESPONSE_FIELDS = {
    "id",
    "user",
    "company_name",
    "position_name",
    "application_status",
    "current_stage",
    "application_time",
    "ai_interview_time",
    "written_test_time",
    "first_interview_time",
    "second_interview_time",
    "third_interview_time",
    "hr_interview_time",
    "notes",
    "created_at",
    "updated_at",
}
PAGE_FIELDS = {"count", "page", "page_size", "total_pages", "next", "previous", "results"}


@pytest.fixture
def client():
    return Client()


def _register(client, username_prefix: str = "app003"):
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
def auth_session(client):
    return _login(client, _register(client))


@pytest.fixture
def second_auth_session(client):
    return _login(client, _register(client, "other003"))


def _auth_headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _create_application(client, session, company_name):
    response = client.post(
        APPLICATIONS_URL,
        {"company_name": company_name, "position_name": "后端工程师"},
        content_type="application/json",
        **_auth_headers(session),
    )
    assert response.status_code == 201
    return response.json()


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _assert_complete_record(record):
    assert RESPONSE_FIELDS <= set(record)
    assert "password" not in record
    assert "password_hash" not in record
    assert "access" not in record
    assert "refresh" not in record


@pytest.mark.django_db
def test_authenticated_list_returns_default_pagination_container_and_own_records(
    client, auth_session
):
    created = _create_application(client, auth_session, "本人列表科技")

    response = client.get(APPLICATIONS_URL, **_auth_headers(auth_session))

    assert response.status_code == 200
    body = _json(response)
    assert PAGE_FIELDS <= set(body)
    assert body["count"] == 1
    assert body["page"] == 1
    assert body["page_size"] >= 1
    assert body["total_pages"] == 1
    assert body["next"] is None
    assert body["previous"] is None
    assert len(body["results"]) == 1
    _assert_complete_record(body["results"][0])
    assert body["results"][0]["id"] == created["id"]
    assert body["results"][0]["user"] == auth_session["user"].id


@pytest.mark.django_db
def test_authenticated_detail_returns_complete_record_for_current_user(client, auth_session):
    created = _create_application(client, auth_session, "本人详情科技")

    response = client.get(
        f"{APPLICATIONS_URL}{created['id']}/", **_auth_headers(auth_session)
    )

    assert response.status_code == 200
    body = _json(response)
    _assert_complete_record(body)
    assert body["id"] == created["id"]
    assert body["user"] == auth_session["user"].id


@pytest.mark.django_db
def test_two_users_are_isolated_in_list_and_detail(
    client, auth_session, second_auth_session
):
    own = _create_application(client, auth_session, "用户一科技")
    other = _create_application(client, second_auth_session, "用户二科技")

    own_list = _json(client.get(APPLICATIONS_URL, **_auth_headers(auth_session)))
    other_list = _json(
        client.get(APPLICATIONS_URL, **_auth_headers(second_auth_session))
    )

    assert {item["id"] for item in own_list["results"]} == {own["id"]}
    assert {item["id"] for item in other_list["results"]} == {other["id"]}
    assert own["id"] not in {item["id"] for item in other_list["results"]}
    assert other["id"] not in {item["id"] for item in own_list["results"]}

    own_detail = client.get(
        f"{APPLICATIONS_URL}{own['id']}/", **_auth_headers(auth_session)
    )
    assert own_detail.status_code == 200


@pytest.mark.django_db
def test_guessing_other_or_nonexistent_id_returns_same_not_found_shape(
    client, auth_session, second_auth_session
):
    other = _create_application(client, second_auth_session, "不可见科技")
    missing_id = 987654321

    other_response = client.get(
        f"{APPLICATIONS_URL}{other['id']}/", **_auth_headers(auth_session)
    )
    missing_response = client.get(
        f"{APPLICATIONS_URL}{missing_id}/", **_auth_headers(auth_session)
    )

    assert other_response.status_code == 404
    assert missing_response.status_code == 404
    assert _json(other_response).get("code") == _json(missing_response).get("code")


@pytest.mark.django_db
def test_empty_list_is_a_successful_empty_pagination_container(client, auth_session):
    response = client.get(APPLICATIONS_URL, **_auth_headers(auth_session))

    assert response.status_code == 200
    body = _json(response)
    assert PAGE_FIELDS <= set(body)
    assert body["count"] == 0
    assert body["results"] == []
    assert body["page"] == 1
    assert body["total_pages"] == 0
    assert body["next"] is None
    assert body["previous"] is None


@pytest.mark.django_db
def test_user_query_cannot_bypass_server_side_ownership(
    client, auth_session, second_auth_session
):
    own = _create_application(client, auth_session, "查询用户一科技")
    other = _create_application(client, second_auth_session, "查询用户二科技")

    response = client.get(
        f"{APPLICATIONS_URL}?user={second_auth_session['user'].id}",
        **_auth_headers(auth_session),
    )

    assert response.status_code in {200, 400}
    if response.status_code == 200:
        body = _json(response)
        returned_ids = {item["id"] for item in body["results"]}
        assert own["id"] in returned_ids
        assert other["id"] not in returned_ids


@pytest.mark.django_db
def test_unauthenticated_list_and_detail_return_401(client):
    list_response = client.get(APPLICATIONS_URL)
    detail_response = client.get(f"{APPLICATIONS_URL}1/")

    assert list_response.status_code == 401
    assert detail_response.status_code == 401
