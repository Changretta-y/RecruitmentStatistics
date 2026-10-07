"""APP-010 black-box tests for the unified application status contract."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.contrib.auth import get_user_model
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


@pytest.fixture
def client():
    return Client()


def _register_and_login(client, prefix="app010"):
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
    logged_in = client.post(
        LOGIN_URL, credentials, content_type="application/json"
    )
    assert logged_in.status_code == 200
    return {"access": logged_in.json()["access"], "id": registered.json()["id"]}


@pytest.fixture
def owner(client):
    return _register_and_login(client)


@pytest.fixture
def other_user(client):
    return _register_and_login(client, "other010")


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _position(name="后端开发", status=None, *, interviews=None):
    result = {
        "position_name": name,
        "application_time": None,
        "notes": f"{name} notes",
        "interviews": interviews or [],
    }
    if status is not None:
        result["application_status"] = status
    return result


def _company_payload(company_name="示例科技", positions=None, shared_stages=None):
    return {
        "company_name": company_name,
        "shared_stages": (
            [
                {"type": stage, "scheduled_at": None, "duration_minutes": None}
                for stage in ("ai_interview", "assessment", "written_test")
            ]
            if shared_stages is None
            else shared_stages
        ),
        "positions": positions if positions is not None else [_position()],
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


@pytest.mark.django_db
@pytest.mark.parametrize("status", CANONICAL_STATUSES)
def test_each_canonical_status_is_accepted_and_is_the_only_public_projection(
    client, owner, status
):
    response = _create(
        client,
        owner,
        _company_payload(positions=[_position(status=status)]),
    )

    assert response.status_code == 201
    body = _json(response)
    assert body["positions"][0]["application_status"] == status
    assert body.get("application_status", status) == status
    assert body.get("current_stage", status) == status


@pytest.mark.django_db
def test_missing_status_defaults_to_applied(client, owner):
    response = _create(client, owner, _company_payload(positions=[_position()]))

    assert response.status_code == 201
    body = _json(response)
    assert body["positions"][0]["application_status"] == "applied"
    assert body.get("application_status", "applied") == "applied"
    assert body.get("current_stage", "applied") == "applied"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_status",
    ["in_progress", "offer", "withdrawn", "ai_interview", "已投递", "unknown"],
)
def test_legacy_and_unknown_statuses_are_rejected_without_partial_write(
    client, owner, invalid_status
):
    before = _json(client.get(APPLICATIONS_URL, **_headers(owner)))
    response = _create(
        client,
        owner,
        _company_payload(
            positions=[
                _position("合法岗位", status="applied"),
                _position("非法岗位", status=invalid_status),
            ]
        ),
    )

    assert response.status_code == 400
    body = _json(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert _details_contain(body, "application_status")
    after = _json(client.get(APPLICATIONS_URL, **_headers(owner)))
    assert after["count"] == before["count"]


@pytest.mark.django_db
def test_status_patch_updates_projection_but_preserves_schedule_and_duration(
    client, owner
):
    scheduled = "2026-10-11T09:00:00+08:00"
    created = _create(
        client,
        owner,
        _company_payload(
            shared_stages=[
                {"type": "ai_interview", "scheduled_at": None, "duration_minutes": None},
                {"type": "assessment", "scheduled_at": scheduled, "duration_minutes": 45},
                {"type": "written_test", "scheduled_at": None, "duration_minutes": None},
            ],
            positions=[
                _position(
                    status="applied",
                    interviews=[
                        {
                            "name": "技术面",
                            "scheduled_at": scheduled,
                            "duration_minutes": 90,
                        }
                    ],
                )
            ],
        ),
    )
    assert created.status_code == 201
    original = _json(created)
    assert original["positions"][0]["application_status"] == "applied"
    assert original.get("current_stage", "applied") == "applied"

    changed = _patch(
        client,
        owner,
        original["id"],
        {
            "positions": [
                {"id": original["positions"][0]["id"], "application_status": "second_interview"}
            ]
        },
    )

    assert changed.status_code == 200
    body = _json(changed)
    assert body["positions"][0]["application_status"] == "second_interview"
    assert body.get("application_status", "second_interview") == "second_interview"
    assert body.get("current_stage", "second_interview") == "second_interview"
    assessment = next(stage for stage in body["shared_stages"] if stage["type"] == "assessment")
    assert assessment["scheduled_at"] is not None
    assert assessment["duration_minutes"] == 45
    assert body["positions"][0]["interviews"][0]["scheduled_at"] is not None
    assert body["positions"][0]["interviews"][0]["duration_minutes"] == 90


@pytest.mark.django_db
def test_schedule_changes_do_not_derive_or_change_application_status(client, owner):
    created = _create(
        client,
        owner,
        _company_payload(positions=[_position(status="applied")]),
    )
    assert created.status_code == 201
    company = _json(created)
    position = company["positions"][0]

    with_assessment = _patch(
        client,
        owner,
        company["id"],
        {
            "shared_stages": [
                {
                    "type": "assessment",
                    "scheduled_at": "2026-10-12T09:00:00+08:00",
                    "duration_minutes": 60,
                }
            ]
        },
    )
    assert with_assessment.status_code == 200
    assert _json(with_assessment)["positions"][0]["application_status"] == "applied"
    assert _json(with_assessment).get("current_stage", "applied") == "applied"

    cleared = _patch(
        client,
        owner,
        company["id"],
        {"shared_stages": [{"type": "assessment", "scheduled_at": None}]},
    )
    assert cleared.status_code == 200
    assert _json(cleared)["positions"][0]["application_status"] == "applied"
    assert _json(cleared).get("current_stage", "applied") == "applied"

    added_interview = client.post(
        f"{APPLICATIONS_URL}{company['id']}/positions/{position['id']}/interviews/",
        {
            "name": "一面",
            "scheduled_at": "2026-10-13T09:00:00+08:00",
            "duration_minutes": 60,
        },
        content_type="application/json",
        **_headers(owner),
    )
    assert added_interview.status_code == 201
    detail = client.get(f"{APPLICATIONS_URL}{company['id']}/", **_headers(owner))
    assert detail.status_code == 200
    assert _json(detail)["positions"][0]["application_status"] == "applied"
    assert _json(detail).get("current_stage", "applied") == "applied"


@pytest.mark.django_db
def test_application_status_filter_matches_any_position_and_stage_is_rejected(
    client, owner
):
    target = _create(
        client,
        owner,
        _company_payload(
            company_name="多岗位筛选公司",
            positions=[
                _position("后端", status="applied"),
                _position("数据", status="second_interview"),
            ],
        ),
    )
    assert target.status_code == 201
    target_body = _json(target)
    other = _create(
        client,
        owner,
        _company_payload(
            company_name="其他筛选公司",
            positions=[_position("前端", status="rejected")],
        ),
    )
    assert other.status_code == 201

    for query in (
        "application_status=second_interview",
        "application_status=applied,second_interview",
        "application_status=applied&application_status=second_interview",
    ):
        listing = client.get(f"{APPLICATIONS_URL}?{query}", **_headers(owner))
        assert listing.status_code == 200
        page = _json(listing)
        assert page["count"] == 1
        assert page["results"][0]["id"] == target_body["id"]
        assert len(page["results"][0]["positions"]) == 2

    invalid = client.get(
        f"{APPLICATIONS_URL}?application_status=in_progress", **_headers(owner)
    )
    assert invalid.status_code == 400
    assert _details_contain(_json(invalid), "application_status")
    old_stage = client.get(f"{APPLICATIONS_URL}?stage=first_interview", **_headers(owner))
    assert old_stage.status_code == 400
    assert _details_contain(_json(old_stage), "stage")


@pytest.mark.django_db
def test_flat_compatibility_write_uses_canonical_status_and_main_position_projection(
    client, owner
):
    response = _create(
        client,
        owner,
        {
            "company_name": "兼容写入公司",
            "position_name": "后端开发",
            "application_status": "hr_interview",
            "application_time": None,
            "notes": "兼容客户端",
        },
    )
    assert response.status_code == 201
    body = _json(response)
    assert body["positions"][0]["application_status"] == "hr_interview"
    assert body.get("application_status", "hr_interview") == "hr_interview"
    assert body.get("current_stage", "hr_interview") == "hr_interview"


@pytest.mark.django_db
def test_multi_position_statuses_are_independent_and_shared_projection_is_read_only(
    client, owner, other_user
):
    created = _create(
        client,
        owner,
        _company_payload(
            company_name="岗位隔离公司",
            positions=[
                _position("后端", status="first_interview"),
                _position("前端", status="rejected"),
            ],
        ),
    )
    assert created.status_code == 201
    company = _json(created)
    first, second = company["positions"]

    changed = _patch(
        client,
        owner,
        company["id"],
        {"positions": [{"id": second["id"], "application_status": "hr_interview"}]},
    )
    assert changed.status_code == 200
    body = _json(changed)
    by_id = {item["id"]: item for item in body["positions"]}
    assert by_id[first["id"]]["application_status"] == "first_interview"
    assert by_id[second["id"]]["application_status"] == "hr_interview"
    assert body.get("current_stage", "first_interview") == "first_interview"

    foreign = client.get(f"{APPLICATIONS_URL}{company['id']}/", **_headers(other_user))
    assert foreign.status_code == 404

    target_created = _create(
        client,
        other_user,
        _company_payload(
            company_name="共享目标公司",
            positions=[_position("共享岗位", status="first_interview")],
        ),
    )
    assert target_created.status_code == 201

    request = client.post(
        f"{SHARING_URL}requests/",
        {"recipient_id": other_user["id"]},
        content_type="application/json",
        **_headers(owner),
    )
    assert request.status_code == 201
    request_body = _json(request)
    accepted = client.post(
        f"{SHARING_URL}requests/{request_body['id']}/respond/",
        {"decision": "accepted"},
        content_type="application/json",
        **_headers(other_user),
    )
    assert accepted.status_code == 200
    shared = client.get(
        f"{SHARING_URL}users/{other_user['id']}/applications/",
        **_headers(owner),
    )
    assert shared.status_code == 200
    shared_body = _json(shared)
    assert shared_body["results"][0]["application_status"] == "first_interview"
    assert shared_body["results"][0]["current_stage"] == "first_interview"


@pytest.mark.django_db(transaction=True)
def test_historical_status_values_migrate_to_canonical_public_statuses(client):
    """Seed the documented pre-APP-009 schema and inspect only public output."""
    executor = MigrationExecutor(connection)
    old_target = ("applications", "0003_jobapplication_stage_durations")
    latest_targets = executor.loader.graph.leaf_nodes()
    user = get_user_model().objects.create_user(
        username=f"app010migration{uuid.uuid4().hex[:8]}",
        email="app010migration@example.com",
        password=PASSWORD,
    )

    timestamp = datetime(2026, 10, 8, 1, 0, tzinfo=timezone.utc)
    historical_rows = [
        ("in_progress", "written_test", {"written_test_time": timestamp, "written_test_duration_minutes": 42}),
        ("in_progress", "first_interview", {"first_interview_time": timestamp, "first_interview_duration_minutes": 51}),
        ("in_progress", "second_interview", {"second_interview_time": timestamp, "second_interview_duration_minutes": 52}),
        ("in_progress", "other_interview", {"third_interview_time": timestamp, "third_interview_duration_minutes": 53}),
        ("in_progress", "hr_interview", {"hr_interview_time": timestamp, "hr_interview_duration_minutes": 54}),
        ("in_progress", "applied", {"ai_interview_time": timestamp, "ai_interview_duration_minutes": 30}),
        ("in_progress", "applied", {}),
        ("offer", "rejected", {}),
        ("withdrawn", "rejected", {}),
        ("applied", "applied", {}),
        ("rejected", "rejected", {}),
    ]

    try:
        executor.migrate([old_target])
        historical_model = MigrationExecutor(connection).loader.project_state(
            [old_target]
        ).apps.get_model("applications", "JobApplication")
        for index, (old_status, expected_status, stages) in enumerate(historical_rows):
            values = {
                "user_id": user.pk,
                "company_name": f"历史迁移公司{index}",
                "position_name": f"历史岗位{index}",
                "application_status": old_status,
                "notes": f"保留备注{index}",
                "application_url": f"https://example.invalid/history/{index}",
                "ai_interview_time": None,
                "ai_interview_duration_minutes": None,
                "written_test_time": None,
                "written_test_duration_minutes": None,
                "first_interview_time": None,
                "first_interview_duration_minutes": None,
                "second_interview_time": None,
                "second_interview_duration_minutes": None,
                "third_interview_time": None,
                "third_interview_duration_minutes": None,
                "hr_interview_time": None,
                "hr_interview_duration_minutes": None,
            }
            values.update(stages)
            historical_model.objects.create(**values)

        MigrationExecutor(connection).migrate(latest_targets)
        logged_in = client.post(
            LOGIN_URL,
            {"username": user.username, "password": PASSWORD},
            content_type="application/json",
        )
        assert logged_in.status_code == 200
        session = {"access": logged_in.json()["access"]}
        listing = client.get(APPLICATIONS_URL, **_headers(session))
        assert listing.status_code == 200
        companies = _json(listing)["results"]
        assert len(companies) == len(historical_rows)
        positions = {
            item["position_name"]: item
            for company in companies
            for item in company["positions"]
        }
        assert [positions[f"历史岗位{i}"]["application_status"] for i in range(len(historical_rows))] == [
            expected for _, expected, _ in historical_rows
        ]
        assert positions["历史岗位0"]["notes"] == "保留备注0"
        assert positions["历史岗位0"]["application_url"] == "https://example.invalid/history/0"
        written_company = next(
            company
            for company in companies
            if company["positions"][0]["position_name"] == "历史岗位0"
        )
        written_stage = next(
            stage
            for stage in written_company["shared_stages"]
            if stage["type"] == "written_test"
        )
        assert written_stage["scheduled_at"] is not None
        assert written_stage["duration_minutes"] == 42
    finally:
        MigrationExecutor(connection).migrate(latest_targets)
