"""Black-box tests for APP-006 partial update and stage-time clearing APIs."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
PASSWORD = "StrongPass_123"
STAGE_FIELDS = (
    "ai_interview_time",
    "written_test_time",
    "first_interview_time",
    "second_interview_time",
    "third_interview_time",
    "hr_interview_time",
)
MUTABLE_FIELDS = {
    "company_name",
    "position_name",
    "application_status",
    "application_time",
    *STAGE_FIELDS,
    "notes",
}


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
    return _login(client, _register(client, "app006owner"))


@pytest.fixture
def other_user(client):
    return _login(client, _register(client, "app006other"))


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _create(client, session, **overrides):
    payload = {
        "company_name": "初始科技",
        "position_name": "初始岗位",
        "application_status": "in_progress",
        "application_time": "2026-01-10T09:00:00+08:00",
        "ai_interview_time": "2026-01-11T09:00:00+08:00",
        "written_test_time": None,
        "first_interview_time": None,
        "second_interview_time": None,
        "third_interview_time": None,
        "hr_interview_time": None,
        "notes": "原始备注",
    }
    payload.update(overrides)
    response = client.post(
        APPLICATIONS_URL,
        payload,
        content_type="application/json",
        **_headers(session),
    )
    assert response.status_code == 201
    return response.json()


def _patch(client, session, application_id, payload):
    return client.patch(
        f"{APPLICATIONS_URL}{application_id}/",
        payload,
        content_type="application/json",
        **_headers(session),
    )


@pytest.mark.django_db
def test_patch_one_field_preserves_other_mutable_fields_and_returns_full_record(
    client, owner
):
    created = _create(client, owner)

    response = _patch(client, owner, created["id"], {"notes": "修改后的备注"})

    assert response.status_code == 200
    body = _json(response)
    assert set(created) <= set(body)
    assert body["notes"] == "修改后的备注"
    for field in MUTABLE_FIELDS - {"notes"}:
        assert body[field] == created[field]
    assert body["id"] == created["id"]
    assert body["user"] == owner["user"].id
    assert body["created_at"] == created["created_at"]
    assert "password" not in body
    assert "access" not in body
    assert "refresh" not in body


@pytest.mark.django_db
@pytest.mark.parametrize("stage_field", STAGE_FIELDS)
def test_each_stage_can_be_set_modified_and_cleared_with_derived_current_stage(
    client, owner, stage_field
):
    created = _create(
        client,
        owner,
        application_status="applied",
        ai_interview_time=None,
    )
    stage_name = stage_field.removesuffix("_time")
    first_time = "2026-02-10T10:00:00+08:00"
    second_time = "2026-03-10T10:00:00+08:00"

    set_response = _patch(client, owner, created["id"], {stage_field: first_time})
    assert set_response.status_code == 200
    set_body = _json(set_response)
    assert set_body[stage_field] is not None
    assert set_body["current_stage"] == stage_name

    modify_response = _patch(client, owner, created["id"], {stage_field: second_time})
    assert modify_response.status_code == 200
    modify_body = _json(modify_response)
    assert modify_body[stage_field] is not None
    assert modify_body["current_stage"] == stage_name
    assert modify_body[stage_field] != set_body[stage_field]

    clear_response = _patch(client, owner, created["id"], {stage_field: None})
    assert clear_response.status_code == 200
    clear_body = _json(clear_response)
    assert clear_body[stage_field] is None
    assert clear_body["current_stage"] == "applied"


@pytest.mark.django_db
def test_patch_aware_iso_time_round_trips_as_aware_utc_time(client, owner):
    created = _create(client, owner, application_time=None)

    response = _patch(
        client,
        owner,
        created["id"],
        {"application_time": "2026-09-20T10:00:00+08:00"},
    )

    assert response.status_code == 200
    body = _json(response)
    parsed = datetime.fromisoformat(body["application_time"].replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.astimezone(timezone.utc) == datetime(
        2026, 9, 20, 2, 0, tzinfo=timezone.utc
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"application_time": "not-an-iso-time"}, "application_time"),
        ({"application_time": ""}, "application_time"),
        ({"ai_interview_time": ""}, "ai_interview_time"),
        ({"application_status": "unknown"}, "application_status"),
    ],
)
def test_invalid_time_empty_string_or_status_returns_field_error_without_mutation(
    client, owner, payload, field
):
    created = _create(client, owner)

    response = _patch(client, owner, created["id"], payload)

    assert response.status_code == 400
    body = _json(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert field in body["details"]

    unchanged = _json(client.get(f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner)))
    assert unchanged[field] == created[field]


@pytest.mark.django_db
def test_read_only_fields_cannot_change_owner_id_or_creation_audit_fields(client, owner, other_user):
    created = _create(client, owner)
    forged = {
        "id": created["id"] + 999999,
        "user": other_user["user"].id,
        "current_stage": "offer",
        "created_at": "2000-01-01T00:00:00Z",
        "updated_at": "2000-01-01T00:00:00Z",
        "notes": "合法字段仍可更新",
    }

    response = _patch(client, owner, created["id"], forged)

    assert response.status_code in {200, 400}
    if response.status_code == 200:
        body = _json(response)
        assert body["id"] == created["id"]
        assert body["user"] == owner["user"].id
        assert body["created_at"] == created["created_at"]
        assert body["current_stage"] != "offer"
        assert body["notes"] == "合法字段仍可更新"
    else:
        body = _json(response)
        assert body["code"] == "VALIDATION_ERROR"
        unchanged = _json(
            client.get(f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner))
        )
        assert unchanged["notes"] == created["notes"]
        assert unchanged["user"] == owner["user"].id


@pytest.mark.django_db
def test_cross_user_patch_returns_404_and_leaves_owner_record_unchanged(
    client, owner, other_user
):
    created = _create(client, owner)

    response = _patch(client, other_user, created["id"], {"notes": "越权修改"})

    assert response.status_code == 404
    unchanged = _json(client.get(f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner)))
    assert unchanged["notes"] == created["notes"]
    assert unchanged["user"] == owner["user"].id


@pytest.mark.django_db
def test_unauthenticated_patch_returns_401_and_leaves_record_unchanged(client, owner):
    created = _create(client, owner)

    response = client.patch(
        f"{APPLICATIONS_URL}{created['id']}/",
        {"notes": "匿名修改"},
        content_type="application/json",
    )

    assert response.status_code == 401
    unchanged = _json(client.get(f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner)))
    assert unchanged["notes"] == created["notes"]
