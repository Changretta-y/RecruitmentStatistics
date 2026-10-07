"""APP-011 black-box tests for latest application-flow status projections."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
SHARING_URL = "/api/v1/sharing/"
PASSWORD = "StrongPass_123"

CANONICAL_STATUSES = (
    "applied",
    "assessment",
    "written_test",
    "first_interview",
    "second_interview",
    "other_interview",
    "hr_interview",
    "rejected",
)
LEGACY_STATUSES = ("in_progress", "offer", "withdrawn", "ai_interview", "已投递", "unknown")
SHARED_TYPES = ("ai_interview", "assessment", "written_test")


@pytest.fixture
def client():
    return Client()


def _register_and_login(client, prefix="app011"):
    username = f"{prefix}{uuid.uuid4().hex[:12]}"
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


@pytest.fixture
def owner(client):
    return _register_and_login(client)


@pytest.fixture
def viewer(client):
    return _register_and_login(client, "viewer011")


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _position(name="后端开发", status="applied", interviews=None):
    return {
        "position_name": name,
        "application_status": status,
        "application_time": None,
        "notes": f"{name} notes",
        "interviews": interviews or [],
    }


def _shared_stages(overrides=None):
    values = {
        stage_type: {"scheduled_at": None, "duration_minutes": None}
        for stage_type in SHARED_TYPES
    }
    for stage_type, stage in (overrides or {}).items():
        values[stage_type] = stage
    return [
        {"type": stage_type, **values[stage_type]}
        for stage_type in SHARED_TYPES
    ]


def _company_payload(
    *,
    company_name="APP-011公开公司",
    status="applied",
    interviews=None,
    shared=None,
):
    return {
        "company_name": company_name,
        "shared_stages": _shared_stages(shared),
        "positions": [_position(status=status, interviews=interviews)],
    }


def _create(client, session, payload):
    return client.post(
        APPLICATIONS_URL,
        payload,
        content_type="application/json",
        **_headers(session),
    )


def _patch(client, session, company_id, payload):
    return client.patch(
        f"{APPLICATIONS_URL}{company_id}/",
        payload,
        content_type="application/json",
        **_headers(session),
    )


def _details_contain(body, field):
    return field in json.dumps(body.get("details", {}), ensure_ascii=False)


def _instant(value):
    """Compare public ISO timestamps by instant, regardless of offset spelling."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@pytest.mark.django_db
@pytest.mark.parametrize("status", CANONICAL_STATUSES)
def test_canonical_statuses_remain_accepted_and_legacy_values_remain_rejected(
    client, owner, status
):
    response = _create(client, owner, _company_payload(status=status))
    assert response.status_code == 201
    body = _json(response)
    assert body["positions"][0]["application_status"] == status


@pytest.mark.django_db
@pytest.mark.parametrize("status", LEGACY_STATUSES)
def test_legacy_statuses_are_rejected_without_creating_a_company(client, owner, status):
    before = _json(client.get(APPLICATIONS_URL, **_headers(owner)))
    response = _create(client, owner, _company_payload(status=status))
    assert response.status_code == 400
    body = _json(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert _details_contain(body, "application_status")
    after = _json(client.get(APPLICATIONS_URL, **_headers(owner)))
    assert after["count"] == before["count"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("assessment", "assessment"),
        ("written_test", "written_test"),
        ("ai_interview", "other_interview"),
        ("一面", "first_interview"),
        ("二面", "second_interview"),
        ("HR面", "hr_interview"),
        ("终面", "other_interview"),
    ],
)
def test_current_stage_projects_each_shared_or_position_flow_source(
    client, owner, source, expected
):
    scheduled = "2026-10-20T09:00:00+08:00"
    shared = {source: {"scheduled_at": scheduled, "duration_minutes": 60}} if source in SHARED_TYPES else None
    interviews = (
        [{"name": source, "scheduled_at": scheduled, "duration_minutes": 60}]
        if source not in SHARED_TYPES
        else None
    )
    response = _create(
        client,
        owner,
        _company_payload(shared=shared, interviews=interviews),
    )
    assert response.status_code == 201
    body = _json(response)
    position = body["positions"][0]
    assert position.get("application_status") == "applied"
    assert position.get("current_stage") == expected
    assert body.get("current_stage") == expected


@pytest.mark.django_db
def test_current_stage_uses_latest_time_then_fixed_priority_and_rejected_wins(
    client, owner
):
    same_time = "2026-10-21T09:00:00+08:00"
    all_sources = _create(
        client,
        owner,
        _company_payload(
            shared={
                "assessment": {"scheduled_at": same_time, "duration_minutes": 30},
                "written_test": {"scheduled_at": same_time, "duration_minutes": 30},
                "ai_interview": {"scheduled_at": same_time, "duration_minutes": 30},
            },
            interviews=[
                {"name": "一面", "scheduled_at": same_time, "duration_minutes": 30},
                {"name": "二面", "scheduled_at": same_time, "duration_minutes": 30},
                {"name": "复试", "scheduled_at": same_time, "duration_minutes": 30},
                {"name": "HR面", "scheduled_at": same_time, "duration_minutes": 30},
            ],
        ),
    )
    assert all_sources.status_code == 201
    all_body = _json(all_sources)
    assert all_body["positions"][0].get("current_stage") == "hr_interview"

    rejected = _create(
        client,
        owner,
        _company_payload(
            company_name="APP-011拒绝优先",
            status="rejected",
            interviews=[
                {"name": "HR面", "scheduled_at": same_time, "duration_minutes": 30}
            ],
        ),
    )
    assert rejected.status_code == 201
    rejected_body = _json(rejected)
    assert rejected_body["positions"][0].get("current_stage") == "rejected"

    fallback = _create(
        client,
        owner,
        _company_payload(company_name="APP-011无日程回退", status="second_interview"),
    )
    assert fallback.status_code == 201
    fallback_body = _json(fallback)
    assert fallback_body["positions"][0].get("current_stage") == "second_interview"


@pytest.mark.django_db
def test_schedule_projection_and_saved_status_are_independent(client, owner):
    scheduled = "2026-10-22T09:00:00+08:00"
    created = _create(
        client,
        owner,
        _company_payload(
            shared={"assessment": {"scheduled_at": scheduled, "duration_minutes": 45}}
        ),
    )
    assert created.status_code == 201
    body = _json(created)
    position = body["positions"][0]
    assert position["application_status"] == "applied"
    assert position.get("current_stage") == "assessment"

    changed = _patch(
        client,
        owner,
        body["id"],
        {"positions": [{"id": position["id"], "application_status": "second_interview"}]},
    )
    assert changed.status_code == 200
    changed_body = _json(changed)
    changed_position = changed_body["positions"][0]
    assert changed_position["application_status"] == "second_interview"
    assert changed_position.get("current_stage") == "assessment"
    assessment = next(stage for stage in changed_body["shared_stages"] if stage["type"] == "assessment")
    assert _instant(assessment["scheduled_at"]) == _instant(scheduled)
    assert assessment["duration_minutes"] == 45


@pytest.mark.django_db
def test_list_filter_and_shared_read_only_response_use_current_stage(client, owner, viewer):
    created = _create(
        client,
        viewer,
        _company_payload(
            company_name="APP-011共享最新状态",
            shared={"written_test": {"scheduled_at": "2026-10-23T09:00:00+08:00", "duration_minutes": 60}},
        ),
    )
    assert created.status_code == 201
    created_body = _json(created)
    position = created_body["positions"][0]
    assert position.get("current_stage") == "written_test"

    filtered = client.get(
        f"{APPLICATIONS_URL}?application_status=written_test",
        **_headers(viewer),
    )
    assert filtered.status_code == 200
    filtered_body = _json(filtered)
    assert filtered_body["count"] == 1
    assert filtered_body["results"][0]["positions"][0].get("current_stage") == "written_test"

    request = client.post(
        f"{SHARING_URL}requests/",
        {"recipient_id": viewer["id"]},
        content_type="application/json",
        **_headers(owner),
    )
    assert request.status_code == 201
    request_body = _json(request)
    accepted = client.post(
        f"{SHARING_URL}requests/{request_body['id']}/respond/",
        {"decision": "accepted"},
        content_type="application/json",
        **_headers(viewer),
    )
    assert accepted.status_code == 200
    shared = client.get(
        f"{SHARING_URL}users/{viewer['id']}/applications/",
        **_headers(owner),
    )
    assert shared.status_code == 200
    shared_body = _json(shared)
    shared_record = shared_body["results"][0]
    assert shared_record["application_status"] == "applied"
    assert shared_record.get("current_stage") == "written_test"
