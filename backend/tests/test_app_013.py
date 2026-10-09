"""APP-013 public HTTP contract for legacy URL backfill on company reuse.

Only authenticated JSON requests and responses are observed here.  No model,
serializer, or view code is imported.
"""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client


REGISTER = "/api/v1/auth/register/"
LOGIN = "/api/v1/auth/login/"
COMPANIES = "/api/v1/companies/"
APPLICATIONS = "/api/v1/applications/"
PASSWORD = "StrongPass_123"


@pytest.fixture
def client():
    return Client()


def _session(client: Client, prefix: str) -> dict[str, str]:
    username = f"{prefix}-{uuid.uuid4().hex[:12]}"
    credentials = {
        "username": username,
        "email": f"{username}@example.test",
        "password": PASSWORD,
    }
    registered = client.post(
        REGISTER,
        {**credentials, "password_confirm": PASSWORD},
        content_type="application/json",
    )
    assert registered.status_code == 201, registered.content
    logged_in = client.post(LOGIN, credentials, content_type="application/json")
    assert logged_in.status_code == 200, logged_in.content
    return {"HTTP_AUTHORIZATION": f"Bearer {logged_in.json()['access']}"}


def _create_company(client: Client, headers: dict[str, str], url: str | None):
    response = client.post(
        COMPANIES,
        {"company_name": "  跨用户示例科技  ", "recruitment_url": url},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 201, response.content
    return response.json()


def _flat_application(client: Client, headers: dict[str, str], *, url: str | None):
    payload = {
        "company_name": "跨用户示例科技",
        "position_name": "B 的私有岗位",
        "application_status": "applied",
        "application_time": None,
        "notes": "B 的私有备注",
    }
    if url is not None:
        payload["application_url"] = url
    return client.post(APPLICATIONS, payload, content_type="application/json", **headers)


def _own_list(client: Client, headers: dict[str, str]):
    response = client.get(APPLICATIONS, **headers)
    assert response.status_code == 200, response.content
    return response.json()["results"]


def _company_detail(client: Client, headers: dict[str, str], company_id: int):
    response = client.get(f"{COMPANIES}{company_id}/", **headers)
    assert response.status_code == 200, response.content
    return response.json()


@pytest.mark.django_db
def test_other_users_legacy_flat_url_backfills_existing_empty_company_and_all_public_projections(client):
    owner = _session(client, "app013-a")
    other = _session(client, "app013-b")
    company = _create_company(client, owner, None)
    assert company["recruitment_url"] is None

    owner_application = client.post(
        APPLICATIONS,
        {
            "company_id": company["id"],
            "positions": [{"position_name": "A 的私有岗位", "application_status": "applied", "notes": "A 的私有备注", "interviews": []}],
            "shared_stages": [],
        },
        content_type="application/json",
        **owner,
    )
    assert owner_application.status_code == 201, owner_application.content
    owner_application_id = owner_application.json()["id"]

    url = "https://jobs.example.test/campus?from=legacy"
    created = _flat_application(client, other, url=url)
    assert created.status_code == 201, created.content
    body = created.json()
    assert body["company_id"] == company["id"]
    assert body["company"]["id"] == company["id"]
    assert body["recruitment_url"] == url
    assert body["company"]["recruitment_url"] == url
    assert body["application_url"] == url

    assert _company_detail(client, owner, company["id"])["recruitment_url"] == url
    assert _company_detail(client, other, company["id"])["recruitment_url"] == url
    owner_list = _own_list(client, owner)
    other_list = _own_list(client, other)
    assert [item["id"] for item in owner_list] == [owner_application_id]
    assert [item["id"] for item in other_list] == [body["id"]]
    for item in (owner_list[0], other_list[0]):
        assert item["company_id"] == company["id"]
        assert item["recruitment_url"] == url
        assert item["company"]["recruitment_url"] == url
    assert owner_list[0]["positions"][0]["notes"] == "A 的私有备注"
    assert other_list[0]["positions"][0]["notes"] == "B 的私有备注"
    assert "B 的私有备注" not in json.dumps(owner_list, ensure_ascii=False)
    assert "A 的私有备注" not in json.dumps(other_list, ensure_ascii=False)


@pytest.mark.django_db
def test_other_users_legacy_flat_url_cannot_replace_existing_company_url(client):
    owner = _session(client, "app013-existing-a")
    other = _session(client, "app013-existing-b")
    original_url = "https://jobs.example.test/original"
    company = _create_company(client, owner, original_url)
    created = _flat_application(client, other, url="https://jobs.example.test/attempted-replacement")
    assert created.status_code == 201, created.content
    body = created.json()
    assert body["company_id"] == company["id"]
    assert body["recruitment_url"] == original_url
    assert body["company"]["recruitment_url"] == original_url
    assert body["application_url"] == original_url
    assert _company_detail(client, owner, company["id"])["recruitment_url"] == original_url
    assert _own_list(client, other)[0]["recruitment_url"] == original_url


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["not-a-valid-url", "javascript:alert(1)"])
def test_invalid_legacy_flat_url_rejects_request_without_partial_company_or_application(client, url):
    owner = _session(client, "app013-invalid-a")
    other = _session(client, "app013-invalid-b")
    company = _create_company(client, owner, None)
    response = _flat_application(client, other, url=url)
    assert response.status_code == 400, response.content
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "application_url" in json.dumps(body.get("details", {}), ensure_ascii=False)
    assert _company_detail(client, owner, company["id"])["recruitment_url"] is None
    assert _own_list(client, other) == []


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["", None])
def test_empty_or_absent_legacy_flat_url_does_not_backfill_company(client, url):
    owner = _session(client, "app013-empty-a")
    other = _session(client, "app013-empty-b")
    company = _create_company(client, owner, None)
    response = _flat_application(client, other, url=url)
    if response.status_code == 201:
        body = response.json()
        assert body["company_id"] == company["id"]
        assert body["recruitment_url"] is None
        assert body["company"]["recruitment_url"] is None
        assert [item["id"] for item in _own_list(client, other)] == [body["id"]]
    else:
        assert response.status_code == 400, response.content
        assert _own_list(client, other) == []
    assert _company_detail(client, owner, company["id"])["recruitment_url"] is None
