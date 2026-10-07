"""WEB-APP-008 black-box API coverage for ordering and page validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
PASSWORD = "StrongPass_123"


@pytest.fixture
def client():
    return Client()


def _session(client):
    username = f"webapp008{uuid.uuid4().hex[:12]}"
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
    logged_in = client.post(LOGIN_URL, credentials, content_type="application/json")
    assert logged_in.status_code == 200
    return {"access": logged_in.json()["access"], "id": registered.json()["id"]}


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _create(client, session, company_name, positions):
    response = client.post(
        APPLICATIONS_URL,
        {"company_name": company_name, "positions": positions},
        content_type="application/json",
        **_headers(session),
    )
    assert response.status_code == 201, response.content
    return _json(response)


def _position(name, status):
    return {
        "position_name": name,
        "application_status": status,
        "application_time": None,
        "notes": f"{name} notes",
    }


@pytest.mark.django_db
def test_default_listing_places_only_all_rejected_companies_after_active_companies(
    client,
):
    session = _session(client)
    _create(client, session, "早期推进公司", [_position("后端", "applied")])
    _create(
        client,
        session,
        "多岗位仍推进公司",
        [_position("已拒绝岗位", "rejected"), _position("仍在推进岗位", "assessment")],
    )
    _create(client, session, "最近全拒绝公司", [_position("拒绝岗位", "rejected")])

    response = client.get(
        f"{APPLICATIONS_URL}?page=1&page_size=10",
        **_headers(session),
    )
    assert response.status_code == 200
    body = _json(response)
    assert [item["company_name"] for item in body["results"]] == [
        "多岗位仍推进公司",
        "早期推进公司",
        "最近全拒绝公司",
    ]
    assert all(
        any(position.get("current_stage", position.get("application_status")) != "rejected" for position in item["positions"])
        for item in body["results"][:2]
    )
    assert all(
        position.get("current_stage", position.get("application_status")) == "rejected"
        for position in body["results"][-1]["positions"]
    )


@pytest.mark.django_db
def test_default_listing_uses_id_desc_when_updated_at_values_are_equal(
    client, monkeypatch
):
    session = _session(client)
    fixed_now = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("django.utils.timezone.now", lambda: fixed_now)

    first = _create(client, session, "同一更新时间较早 ID", [_position("后端", "applied")])
    second = _create(client, session, "同一更新时间较晚 ID", [_position("后端", "applied")])
    assert first["updated_at"] == second["updated_at"]
    assert first["id"] < second["id"]

    response = client.get(
        f"{APPLICATIONS_URL}?page=1&page_size=10&ordering=-updated_at",
        **_headers(session),
    )

    assert response.status_code == 200
    body = _json(response)
    tied = [
        item for item in body["results"]
        if item["updated_at"] == first["updated_at"]
    ]
    assert [item["id"] for item in tied] == [second["id"], first["id"]]


@pytest.mark.django_db
def test_explicit_ordering_does_not_force_rejected_companies_to_the_end(client):
    session = _session(client)
    _create(client, session, "先创建的推进公司", [_position("后端", "applied")])
    _create(client, session, "后创建的拒绝公司", [_position("后端", "rejected")])

    response = client.get(
        f"{APPLICATIONS_URL}?page=1&page_size=10&ordering=-created_at",
        **_headers(session),
    )

    assert response.status_code == 200
    body = _json(response)
    assert [item["company_name"] for item in body["results"]] == [
        "后创建的拒绝公司",
        "先创建的推进公司",
    ]


@pytest.mark.django_db
def test_out_of_range_page_is_empty_and_pagination_links_preserve_query_params(client):
    session = _session(client)
    position = {
        **_position("后端", "applied"),
        "application_time": "2026-01-15T00:00:00Z",
    }
    for index in range(11):
        _create(client, session, f"分页公司{index}", [position])

    query = {
        "page": "1",
        "page_size": "10",
        "search": "分页公司",
        "application_status": "applied",
        "application_time_after": "2026-01-01T00:00:00Z",
        "application_time_before": "2026-12-31T23:59:59Z",
        "ordering": "-created_at",
    }
    first_page = client.get(
        f"{APPLICATIONS_URL}?{urlencode(query)}",
        **_headers(session),
    )
    assert first_page.status_code == 200
    first_body = _json(first_page)
    assert first_body["total_pages"] == 2
    assert parse_qs(urlparse(first_body["next"]).query) == {
        **{key: [value] for key, value in query.items()},
        "page": ["2"],
    }

    out_of_range = client.get(
        f"{APPLICATIONS_URL}?{urlencode({**query, 'page': '3'})}",
        **_headers(session),
    )
    assert out_of_range.status_code == 200
    body = _json(out_of_range)
    assert body["results"] == []
    assert body["count"] == 11
    assert body["total_pages"] == 2
    assert body["next"] is None
    assert parse_qs(urlparse(body["previous"]).query) == {
        **{key: [value] for key, value in query.items()},
        "page": ["2"],
    }


@pytest.mark.django_db
def test_application_list_requires_authentication(client):
    response = client.get(APPLICATIONS_URL)

    assert response.status_code == 401


@pytest.mark.django_db
def test_application_list_is_not_visible_to_another_user(client):
    owner = _session(client)
    other_user = _session(client)
    _create(client, owner, "仅本人可见公司", [_position("后端", "applied")])

    response = client.get(
        f"{APPLICATIONS_URL}?page=1&page_size=10",
        **_headers(other_user),
    )

    assert response.status_code == 200
    body = _json(response)
    assert body["count"] == 0
    assert body["results"] == []
    assert "仅本人可见公司" not in {item["company_name"] for item in body["results"]}


@pytest.mark.django_db
def test_application_list_accepts_search_status_date_and_page_size_parameters(client):
    session = _session(client)
    _create(
        client,
        session,
        "目标搜索公司",
        [_position("目标岗位", "assessment") | {"application_time": "2026-06-15T00:00:00Z"}],
    )
    _create(
        client,
        session,
        "其他状态公司",
        [_position("其他岗位", "rejected") | {"application_time": "2026-01-15T00:00:00Z"}],
    )

    search_response = client.get(
        f"{APPLICATIONS_URL}?page=1&page_size=10&search=目标搜索",
        **_headers(session),
    )
    assert search_response.status_code == 200
    assert [item["company_name"] for item in _json(search_response)["results"]] == [
        "目标搜索公司"
    ]

    status_response = client.get(
        f"{APPLICATIONS_URL}?page=1&page_size=10&application_status=assessment",
        **_headers(session),
    )
    assert status_response.status_code == 200
    assert [item["company_name"] for item in _json(status_response)["results"]] == [
        "目标搜索公司"
    ]

    date_response = client.get(
        f"{APPLICATIONS_URL}?page=1&page_size=10&application_time_after=2026-06-01T00:00:00Z&application_time_before=2026-06-30T23:59:59Z",
        **_headers(session),
    )
    assert date_response.status_code == 200
    assert [item["company_name"] for item in _json(date_response)["results"]] == [
        "目标搜索公司"
    ]

    page_size_response = client.get(
        f"{APPLICATIONS_URL}?page=1&page_size=10",
        **_headers(session),
    )
    assert page_size_response.status_code == 200
    assert _json(page_size_response)["page_size"] == 10


@pytest.mark.django_db
def test_empty_application_list_returns_a_200_empty_page(client):
    session = _session(client)

    response = client.get(
        f"{APPLICATIONS_URL}?page=1&page_size=10",
        **_headers(session),
    )

    assert response.status_code == 200
    body = _json(response)
    assert body["count"] == 0
    assert body["total_pages"] == 0
    assert body["results"] == []


@pytest.mark.django_db
def test_page_999_returns_a_200_empty_result_with_real_pagination_metadata(client):
    session = _session(client)
    _create(client, session, "存在的公司", [_position("后端", "applied")])

    response = client.get(
        f"{APPLICATIONS_URL}?page=999&page_size=10",
        **_headers(session),
    )

    assert response.status_code == 200
    body = _json(response)
    assert body["results"] == []
    assert body["count"] == 1
    assert body["total_pages"] == 1
@pytest.mark.django_db
@pytest.mark.parametrize("page", ["0", "-1", "abc", "1.5", "", "  "])
def test_invalid_page_is_a_field_level_validation_error(client, page):
    session = _session(client)
    response = client.get(
        f"{APPLICATIONS_URL}?page={page}&page_size=10&search=保持条件&ordering=-updated_at",
        **_headers(session),
    )
    assert response.status_code == 400
    body = _json(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert "page" in body["details"]
