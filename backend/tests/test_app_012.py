"""APP-012 black-box HTTP tests for the global company directory contract.

These tests use only registration, authentication, and documented JSON API
requests.  They intentionally do not import application models or production
serializers/views.
"""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
COMPANIES_URL = "/api/v1/companies/"
APPLICATIONS_URL = "/api/v1/applications/"
PASSWORD = "StrongPass_123"


@pytest.fixture
def client():
    return Client()


def _register_and_login(client: Client, prefix: str) -> dict[str, str | int]:
    username = f"{prefix}{uuid.uuid4().hex[:12]}"
    credentials = {
        "username": username,
        "email": f"{username}@example.test",
        "password": PASSWORD,
    }
    registered = client.post(
        REGISTER_URL,
        {**credentials, "password_confirm": PASSWORD},
        content_type="application/json",
    )
    assert registered.status_code == 201, registered.content
    logged_in = client.post(LOGIN_URL, credentials, content_type="application/json")
    assert logged_in.status_code == 200, logged_in.content
    return {
        "access": logged_in.json()["access"],
        "id": registered.json()["id"],
        "username": username,
    }


def _headers(session: dict[str, str | int]) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _company_payload(name: str = "  示例科技  ", url: str | None = "https://jobs.example.test"):
    return {"company_name": name, "recruitment_url": url}


def _position(name: str, *, notes: str, status: str = "applied"):
    return {
        "position_name": name,
        "application_status": status,
        "application_time": None,
        "notes": notes,
        "interviews": [],
    }


def _application_payload(company_id: int, *positions: dict):
    return {
        "company_id": company_id,
        "positions": list(positions),
        "shared_stages": [],
    }


def _create_company(client, session, *, name="  示例科技  ", url="https://jobs.example.test"):
    return client.post(
        COMPANIES_URL,
        _company_payload(name, url),
        content_type="application/json",
        **_headers(session),
    )


def _create_application(client, session, company_id, *positions):
    return client.post(
        APPLICATIONS_URL,
        _application_payload(company_id, *positions),
        content_type="application/json",
        **_headers(session),
    )


@pytest.mark.django_db
def test_global_company_creation_search_normalization_duplicate_and_public_shape(client):
    owner = _register_and_login(client, "app012-owner")
    other = _register_and_login(client, "app012-other")

    assert client.get(COMPANIES_URL).status_code == 401
    assert client.post(
        COMPANIES_URL,
        _company_payload(),
        content_type="application/json",
    ).status_code == 401

    created = _create_company(client, owner)
    assert created.status_code == 201, created.content
    company = _json(created)
    assert company["company_name"] == "示例科技"
    assert company["recruitment_url"] == "https://jobs.example.test"
    company_id = company["id"]

    duplicate = _create_company(
        client,
        other,
        name=" 示例科技 ",
        url="https://jobs.other.example.test",
    )
    assert duplicate.status_code == 409
    duplicate_body = _json(duplicate)
    assert duplicate_body["code"] == "COMPANY_EXISTS"
    assert duplicate_body["details"]["company_id"] == company_id
    assert duplicate_body["details"]["company"]["id"] == company_id
    assert duplicate_body["details"]["company"]["recruitment_url"] == company[
        "recruitment_url"
    ]

    searched = client.get(
        f"{COMPANIES_URL}?search=示例",
        **_headers(other),
    )
    assert searched.status_code == 200
    results = _json(searched)["results"]
    assert [item["id"] for item in results] == [company_id]
    assert results[0]["recruitment_url"] == company["recruitment_url"]

    public_keys = {
        "id",
        "company_name",
        "recruitment_url",
        "created_at",
        "updated_at",
    }
    assert set(results[0]) == public_keys
    private_names = {
        "user",
        "user_id",
        "positions",
        "notes",
        "application_status",
        "current_stage",
        "interviews",
        "shared_stages",
        "application_url",
    }
    assert not private_names.intersection(results[0])


@pytest.mark.django_db
def test_company_reuse_keeps_each_users_application_position_and_interview_private(client):
    owner = _register_and_login(client, "app012-a")
    other = _register_and_login(client, "app012-b")
    created_company = _create_company(client, owner)
    assert created_company.status_code == 201, created_company.content
    company_id = _json(created_company)["id"]

    owner_created = _create_application(
        client,
        owner,
        company_id,
        _position("后端开发", notes="A 的私有备注"),
    )
    assert owner_created.status_code == 201, owner_created.content
    owner_application = _json(owner_created)
    owner_position = owner_application["positions"][0]

    other_created = _create_application(
        client,
        other,
        company_id,
        _position("数据工程师", notes="B 的私有备注", status="second_interview"),
    )
    assert other_created.status_code == 201, other_created.content
    other_application = _json(other_created)
    assert other_application["company_id"] == company_id
    assert other_application["recruitment_url"] == owner_application["recruitment_url"]
    other_position = other_application["positions"][0]

    owner_list = _json(client.get(APPLICATIONS_URL, **_headers(owner)))
    other_list = _json(client.get(APPLICATIONS_URL, **_headers(other)))
    assert [item["id"] for item in owner_list["results"]] == [owner_application["id"]]
    assert [item["id"] for item in other_list["results"]] == [other_application["id"]]
    assert owner_list["results"][0]["positions"][0]["position_name"] == "后端开发"
    assert other_list["results"][0]["positions"][0]["position_name"] == "数据工程师"

    interview_path = (
        f"{APPLICATIONS_URL}{owner_application['id']}/positions/"
        f"{owner_position['id']}/interviews/"
    )
    interview = client.post(
        interview_path,
        {"name": "A 的面试", "scheduled_at": None, "duration_minutes": None},
        content_type="application/json",
        **_headers(owner),
    )
    assert interview.status_code == 201, interview.content
    interview_id = _json(interview)["id"]

    for response in (
        client.get(f"{APPLICATIONS_URL}{owner_application['id']}/", **_headers(other)),
        client.patch(
            f"{APPLICATIONS_URL}{owner_application['id']}/",
            {"positions": [{"id": owner_position["id"], "notes": "越权"}]},
            content_type="application/json",
            **_headers(other),
        ),
        client.get(
            f"{APPLICATIONS_URL}{owner_application['id']}/positions/{owner_position['id']}/",
            **_headers(other),
        ),
        client.get(f"{interview_path}{interview_id}/", **_headers(other)),
        client.delete(
            f"{APPLICATIONS_URL}{other_application['id']}/positions/{other_position['id']}/",
            **_headers(owner),
        ),
    ):
        assert response.status_code == 404, response.content

    owner_detail = client.get(
        f"{APPLICATIONS_URL}{owner_application['id']}/", **_headers(owner)
    )
    assert owner_detail.status_code == 200
    assert _json(owner_detail)["positions"][0]["notes"] == "A 的私有备注"


@pytest.mark.django_db
def test_same_user_company_id_appends_position_and_company_url_is_single_writable_source(client):
    owner = _register_and_login(client, "app012-aggregate")
    created_company = _create_company(client, owner)
    assert created_company.status_code == 201, created_company.content
    company = _json(created_company)
    company_id = company["id"]
    original_url = company["recruitment_url"]

    first = _create_application(
        client,
        owner,
        company_id,
        _position("后端开发", notes="第一岗位"),
    )
    assert first.status_code == 201, first.content
    first_body = _json(first)

    second = _create_application(
        client,
        owner,
        company_id,
        _position("前端开发", notes="第二岗位"),
    )
    assert second.status_code == 201, second.content
    second_body = _json(second)
    assert second_body["id"] == first_body["id"]
    assert second_body["company_id"] == company_id
    assert [p["position_name"] for p in second_body["positions"]] == [
        "后端开发",
        "前端开发",
    ]
    assert all("application_url" not in p for p in second_body["positions"])
    assert all("recruitment_url" not in p for p in second_body["positions"])
    assert second_body["recruitment_url"] == original_url

    rejected = _create_application(
        client,
        owner,
        company_id,
        {
            **_position("不应保存", notes="不应保存"),
            "application_url": "https://position-specific.example.test",
        },
    )
    assert rejected.status_code == 400
    rejected_body = _json(rejected)
    assert rejected_body["code"] == "VALIDATION_ERROR"
    assert "application_url" in json.dumps(
        rejected_body.get("details", {}), ensure_ascii=False
    )
    persisted = _json(
        client.get(f"{APPLICATIONS_URL}{first_body['id']}/", **_headers(owner))
    )
    assert [p["position_name"] for p in persisted["positions"]] == [
        "后端开发",
        "前端开发",
    ]


@pytest.mark.django_db
def test_company_patch_is_shared_and_position_status_update_does_not_change_recruitment_url(client):
    owner = _register_and_login(client, "app012-url-a")
    other = _register_and_login(client, "app012-url-b")
    created_company = _create_company(client, owner)
    assert created_company.status_code == 201, created_company.content
    company_id = _json(created_company)["id"]
    created_application = _create_application(
        client,
        owner,
        company_id,
        _position("后端开发", notes="岗位备注"),
    )
    assert created_application.status_code == 201, created_application.content
    application = _json(created_application)
    position_id = application["positions"][0]["id"]

    patched = client.patch(
        f"{COMPANIES_URL}{company_id}/",
        {"recruitment_url": "https://jobs.shared-updated.example.test"},
        content_type="application/json",
        **_headers(other),
    )
    assert patched.status_code == 200, patched.content
    assert _json(patched)["recruitment_url"] == "https://jobs.shared-updated.example.test"

    owner_company = client.get(f"{COMPANIES_URL}{company_id}/", **_headers(owner))
    assert owner_company.status_code == 200
    assert _json(owner_company)["recruitment_url"] == "https://jobs.shared-updated.example.test"

    status_patch = client.patch(
        f"{APPLICATIONS_URL}{application['id']}/",
        {"positions": [{"id": position_id, "application_status": "second_interview"}]},
        content_type="application/json",
        **_headers(owner),
    )
    assert status_patch.status_code == 200, status_patch.content
    assert _json(status_patch)["recruitment_url"] == "https://jobs.shared-updated.example.test"

    other_company = client.get(f"{COMPANIES_URL}{company_id}/", **_headers(other))
    assert other_company.status_code == 200
    assert _json(other_company)["recruitment_url"] == "https://jobs.shared-updated.example.test"


@pytest.mark.django_db
def test_legacy_flat_application_projects_company_url_and_preserves_canonical_status(client):
    owner = _register_and_login(client, "app012-legacy")
    response = client.post(
        APPLICATIONS_URL,
        {
            "company_name": "兼容示例公司",
            "position_name": "后端开发",
            "application_url": "https://legacy.jobs.example.test",
            "application_status": "second_interview",
            "application_time": None,
            "notes": "兼容客户端备注",
        },
        content_type="application/json",
        **_headers(owner),
    )
    assert response.status_code == 201, response.content
    body = _json(response)
    assert body["company_id"]
    assert body["company"]["id"] == body["company_id"]
    assert body["recruitment_url"] == "https://legacy.jobs.example.test"
    assert body["application_url"] == body["recruitment_url"]
    assert body["positions"][0]["application_status"] == "second_interview"
    assert body["positions"][0]["notes"] == "兼容客户端备注"

