"""Black-box tests for APP-009 company application aggregation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
PASSWORD = "StrongPass_123"

SHARED_TYPES = ("ai_interview", "assessment", "written_test")


@pytest.fixture
def client():
    return Client()


def _register_and_login(client, prefix="app009"):
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
    return {"access": logged_in.json()["access"]}


@pytest.fixture
def owner(client):
    return _register_and_login(client)


@pytest.fixture
def other_user(client):
    return _register_and_login(client, "other009")


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _shared_stages():
    return [
        {"type": stage_type, "scheduled_at": None, "duration_minutes": None}
        for stage_type in SHARED_TYPES
    ]


def _position(name, *, status="applied", interviews=None):
    return {
        "position_name": name,
        "application_status": status,
        "application_time": None,
        "notes": f"{name} notes",
        "interviews": interviews or [],
    }


def _company_payload(company_name="示例科技", positions=None, shared_stages=None):
    return {
        "company_name": company_name,
        "shared_stages": _shared_stages() if shared_stages is None else shared_stages,
        "positions": positions
        if positions is not None
        else [_position("后端开发")],
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


def _position_interviews_url(company_id, position_id):
    return f"{APPLICATIONS_URL}{company_id}/positions/{position_id}/interviews/"


def _position_url(company_id, position_id):
    return f"{APPLICATIONS_URL}{company_id}/positions/{position_id}/"


@pytest.mark.django_db
def test_company_create_returns_multiple_independent_positions_and_shared_stages(
    client, owner
):
    payload = _company_payload(
        positions=[
            _position("后端开发", status="applied"),
            # APP-010 replaces the generic legacy in_progress fixture with an explicit canonical status.
            _position("数据工程师", status="assessment"),
        ]
    )

    response = _create(client, owner, payload)

    assert response.status_code == 201
    body = _json(response)
    assert body["company_name"] == "示例科技"
    assert [position["position_name"] for position in body["positions"]] == [
        "后端开发",
        "数据工程师",
    ]
    assert [position["application_status"] for position in body["positions"]] == [
        "applied",
        "assessment",
    ]
    assert len({position["id"] for position in body["positions"]}) == 2
    assert len(body["shared_stages"]) == 3
    assert {stage["type"] for stage in body["shared_stages"]} == set(SHARED_TYPES)
    assert all(position["notes"] for position in body["positions"])

    listed = client.get(APPLICATIONS_URL, **_headers(owner))
    assert listed.status_code == 200
    page = _json(listed)
    assert page["count"] == 1
    assert [company["id"] for company in page["results"]] == [body["id"]]


@pytest.mark.django_db
def test_patch_adds_position_without_removing_omitted_positions_and_updates_shared_stage(
    client, owner
):
    created_response = _create(
        client,
        owner,
        _company_payload(positions=[_position("后端开发"), _position("测试开发")]),
    )
    assert created_response.status_code == 201
    created = _json(created_response)
    original_positions = {item["id"]: item for item in created["positions"]}
    original_ids = set(original_positions)

    changed_at = "2026-10-12T09:30:00+08:00"
    response = _patch(
        client,
        owner,
        created["id"],
        {
            "shared_stages": [
                {
                    "type": "ai_interview",
                    "scheduled_at": changed_at,
                    "duration_minutes": None,
                }
            ],
            "positions": [
                {
                    "id": next(iter(original_ids)),
                    "position_name": "后端开发（更新）",
                    "application_status": "second_interview",
                    "application_time": "2026-10-01T09:00:00+08:00",
                    "notes": "岗位独立更新",
                },
                _position("算法工程师"),
            ],
        },
    )

    assert response.status_code == 200
    body = _json(response)
    positions = {item["id"]: item for item in body["positions"]}
    assert original_ids <= set(positions)
    assert len(positions) == 3
    updated = positions[next(iter(original_ids))]
    assert updated["position_name"] == "后端开发（更新）"
    assert updated["application_status"] == "second_interview"
    assert updated["notes"] == "岗位独立更新"
    stages = {item["type"]: item for item in body["shared_stages"]}
    assert set(stages) == set(SHARED_TYPES)
    assert stages["ai_interview"]["scheduled_at"] is not None

    persisted = _json(
        client.get(f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner))
    )
    assert len(persisted["positions"]) == 3


@pytest.mark.django_db
def test_shared_stage_type_is_unique_and_setting_it_again_updates_same_record(
    client, owner
):
    created_response = _create(client, owner, _company_payload())
    assert created_response.status_code == 201
    created = _json(created_response)
    first_time = "2026-10-12T09:30:00+08:00"
    second_time = "2026-10-13T10:45:00+08:00"

    first_update = _patch(
        client,
        owner,
        created["id"],
        {
            "shared_stages": [
                {
                    "type": "assessment",
                    "scheduled_at": first_time,
                    "duration_minutes": None,
                }
            ]
        },
    )
    assert first_update.status_code == 200
    second_update = _patch(
        client,
        owner,
        created["id"],
        {
            "shared_stages": [
                {
                    "type": "assessment",
                    "scheduled_at": second_time,
                    "duration_minutes": None,
                }
            ]
        },
    )
    assert second_update.status_code == 200
    stages = _json(second_update)["shared_stages"]
    assert len([stage for stage in stages if stage["type"] == "assessment"]) == 1
    assessment = next(stage for stage in stages if stage["type"] == "assessment")
    assert assessment["scheduled_at"] is not None
    assert assessment["scheduled_at"] != _json(first_update)["shared_stages"][1][
        "scheduled_at"
    ]


@pytest.mark.django_db
def test_one_position_can_have_multiple_interviews_with_repeated_stage_names(
    client, owner
):
    interviews = [
        {
            "name": "技术面",
            "scheduled_at": "2026-10-14T09:00:00+08:00",
            "duration_minutes": 60,
        },
        {
            "name": "技术面",
            "scheduled_at": "2026-10-15T09:00:00+08:00",
            "duration_minutes": 90,
        },
    ]

    response = _create(
        client,
        owner,
        _company_payload(positions=[_position("后端开发", interviews=interviews)]),
    )

    assert response.status_code == 201
    position = _json(response)["positions"][0]
    assert len(position["interviews"]) == 2
    assert [item["name"] for item in position["interviews"]] == ["技术面", "技术面"]
    assert len({item["id"] for item in position["interviews"]}) == 2
    assert [item["duration_minutes"] for item in position["interviews"]] == [60, 90]


@pytest.mark.django_db
def test_interview_subresource_create_patch_and_delete_only_change_target_record(
    client, owner
):
    response = _create(
        client,
        owner,
        _company_payload(positions=[_position("后端开发"), _position("数据工程师")]),
    )
    assert response.status_code == 201
    company = _json(response)
    position, other_position = company["positions"]
    url = _position_interviews_url(company["id"], position["id"])
    first = client.post(
        url,
        {
            "name": "技术面",
            "scheduled_at": "2026-10-14T09:00:00+08:00",
            "duration_minutes": 60,
        },
        content_type="application/json",
        **_headers(owner),
    )
    second = client.post(
        url,
        {
            "name": "技术面",
            "scheduled_at": "2026-10-15T09:00:00+08:00",
            "duration_minutes": 90,
        },
        content_type="application/json",
        **_headers(owner),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    first_item = _json(first)
    second_item = _json(second)
    assert first_item["id"] != second_item["id"]

    updated = client.patch(
        f"{url}{first_item['id']}/",
        {"name": "一面（补充）", "duration_minutes": 75},
        content_type="application/json",
        **_headers(owner),
    )
    assert updated.status_code == 200
    assert _json(updated)["id"] == first_item["id"]
    assert _json(updated)["name"] == "一面（补充）"
    assert _json(updated)["duration_minutes"] == 75

    deleted = client.delete(f"{url}{first_item['id']}/", **_headers(owner))
    assert deleted.status_code == 204
    detail = _json(
        client.get(f"{APPLICATIONS_URL}{company['id']}/", **_headers(owner))
    )
    positions = {item["id"]: item for item in detail["positions"]}
    assert len(positions[position["id"]]["interviews"]) == 1
    assert positions[position["id"]]["interviews"][0]["id"] == second_item["id"]
    assert positions[other_position["id"]]["interviews"] == []


@pytest.mark.django_db
def test_interview_and_position_subresources_are_owner_and_parent_scoped(
    client, owner, other_user
):
    response = _create(client, owner, _company_payload())
    assert response.status_code == 201
    company = _json(response)
    position = company["positions"][0]
    interview_url = _position_interviews_url(company["id"], position["id"])
    interview = client.post(
        interview_url,
        {"name": "一面", "scheduled_at": None, "duration_minutes": None},
        content_type="application/json",
        **_headers(owner),
    )
    assert interview.status_code == 201
    interview_id = _json(interview)["id"]

    foreign_patch = client.patch(
        f"{interview_url}{interview_id}/",
        {"name": "越权修改"},
        content_type="application/json",
        **_headers(other_user),
    )
    wrong_parent = client.patch(
        f"{_position_interviews_url(company['id'], position['id'] + 999)}{interview_id}/",
        {"name": "错误父资源"},
        content_type="application/json",
        **_headers(owner),
    )
    foreign_position_delete = client.delete(
        _position_url(company["id"], position["id"]), **_headers(other_user)
    )

    assert foreign_patch.status_code == 404
    assert wrong_parent.status_code == 404
    assert foreign_position_delete.status_code == 404
    persisted = _json(
        client.get(f"{APPLICATIONS_URL}{company['id']}/", **_headers(owner))
    )
    assert persisted["positions"][0]["interviews"][0]["name"] == "一面"


@pytest.mark.django_db
def test_owner_can_delete_one_position_without_deleting_company_or_sibling_positions(
    client, owner
):
    response = _create(
        client,
        owner,
        _company_payload(positions=[_position("后端开发"), _position("数据工程师")]),
    )
    assert response.status_code == 201
    company = _json(response)
    removed, retained = company["positions"]

    deleted = client.delete(
        _position_url(company["id"], removed["id"]), **_headers(owner)
    )

    assert deleted.status_code == 204
    detail = _json(
        client.get(f"{APPLICATIONS_URL}{company['id']}/", **_headers(owner))
    )
    assert detail["id"] == company["id"]
    assert [position["id"] for position in detail["positions"]] == [retained["id"]]


@pytest.mark.django_db
def test_empty_positions_is_rejected_without_creating_company(client, owner):
    before = _json(client.get(APPLICATIONS_URL, **_headers(owner)))

    response = _create(client, owner, _company_payload(positions=[]))

    assert response.status_code == 400
    error = _json(response)
    assert error["code"] == "VALIDATION_ERROR"
    after = _json(client.get(APPLICATIONS_URL, **_headers(owner)))
    assert after["count"] == before["count"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"company_name": "", "positions": [_position("后端开发")]},
        {"company_name": "有效公司", "positions": [_position("  ")]},
    ],
)
def test_invalid_company_or_position_input_is_rejected_atomically(
    client, owner, invalid_payload
):
    before = _json(client.get(APPLICATIONS_URL, **_headers(owner)))
    payload = _company_payload(**invalid_payload)

    response = _create(client, owner, payload)

    assert response.status_code == 400
    assert _json(response)["code"] == "VALIDATION_ERROR"
    after = _json(client.get(APPLICATIONS_URL, **_headers(owner)))
    assert after["count"] == before["count"]


@pytest.mark.django_db
def test_company_aggregate_is_private_and_detail_is_not_visible_to_other_user(
    client, owner, other_user
):
    response = _create(
        client,
        owner,
        _company_payload(positions=[_position("后端开发"), _position("数据工程师")]),
    )
    assert response.status_code == 201
    company = _json(response)

    other_list = client.get(APPLICATIONS_URL, **_headers(other_user))
    other_detail = client.get(
        f"{APPLICATIONS_URL}{company['id']}/", **_headers(other_user)
    )
    other_patch = _patch(
        client,
        other_user,
        company["id"],
        {"company_name": "被越权修改"},
    )

    assert other_list.status_code == 200
    assert company["id"] not in {item["id"] for item in _json(other_list)["results"]}
    assert other_detail.status_code == 404
    assert other_patch.status_code == 404


@pytest.mark.django_db
def test_normalized_company_post_appends_positions_but_users_stay_isolated(client, owner, other_user):
    original = _create(client, owner, _company_payload("  Example Tech  "))
    assert original.status_code == 201
    again = _create(client, owner, _company_payload("example TECH"))
    assert again.status_code == 201
    assert _json(again)["id"] == _json(original)["id"]
    assert len(_json(again)["positions"]) == 2
    assert _json(client.get(APPLICATIONS_URL, **_headers(owner)))["count"] == 1
    foreign = _create(client, other_user, _company_payload("Example Tech"))
    assert foreign.status_code == 201
    assert _json(foreign)["id"] != _json(original)["id"]


@pytest.mark.django_db
def test_duplicate_shared_types_update_once_and_clear_date_clears_duration(client, owner):
    response = _create(client, owner, _company_payload(shared_stages=[
        {"type": "assessment", "scheduled_at": "2026-10-10T01:00:00Z", "duration_minutes": 35},
        {"type": "assessment", "scheduled_at": "2026-10-11T01:00:00Z", "duration_minutes": 70},
    ]))
    assert response.status_code == 201
    company = _json(response)
    assessments = [item for item in company["shared_stages"] if item["type"] == "assessment"]
    assert len(assessments) == 1
    assert assessments[0]["scheduled_at"].startswith("2026-10-11T01:00:00")
    assert assessments[0]["duration_minutes"] == 70
    # APP-011: the latest scheduled shared assessment is the read-only projection;
    # the saved position status remains applied.
    assert company["current_stage"] == "assessment"
    cleared = _patch(client, owner, company["id"], {"shared_stages": [{"type": "assessment", "scheduled_at": None}]})
    assert cleared.status_code == 200
    assessment = next(item for item in _json(cleared)["shared_stages"] if item["type"] == "assessment")
    assert assessment["scheduled_at"] is None
    assert assessment["duration_minutes"] is None
    assert _json(cleared)["current_stage"] == "applied"


@pytest.mark.django_db
@pytest.mark.parametrize("invalid_stage", [
    {"type": "unknown", "scheduled_at": None},
    {"type": "assessment", "scheduled_at": "invalid-date"},
    {"type": "assessment", "scheduled_at": None, "duration_minutes": 30},
    {"type": "assessment", "scheduled_at": "2026-10-10T01:00:00Z", "duration_minutes": 0},
    {"type": "assessment", "scheduled_at": "2026-10-10T01:00:00Z", "duration_minutes": 1441},
    {"type": "assessment", "scheduled_at": "2026-10-10T01:00:00Z", "duration_minutes": True},
])
def test_invalid_nested_patch_rolls_back_all_parent_and_child_updates(client, owner, invalid_stage):
    created = _create(client, owner, _company_payload())
    assert created.status_code == 201
    original = _json(created)
    response = _patch(client, owner, original["id"], {
        "company_name": "不应保存的名称",
        "positions": [_position("不应新增的岗位")],
        "shared_stages": [invalid_stage],
    })
    assert response.status_code == 400
    assert _json(response)["code"] == "VALIDATION_ERROR"
    detail = client.get(f"{APPLICATIONS_URL}{original['id']}/", **_headers(owner))
    assert _json(detail) == original


@pytest.mark.django_db
def test_nested_interview_patch_keeps_omitted_siblings_and_defaults_durations(client, owner):
    created = _create(client, owner, _company_payload(positions=[_position("后端", interviews=[
        {"name": "一面", "scheduled_at": "2026-10-10T01:00:00Z"},
        {"name": "技术复试", "scheduled_at": "2026-10-12T01:00:00Z", "duration_minutes": 88},
    ])]))
    assert created.status_code == 201
    company = _json(created)
    position = company["positions"][0]
    first, second = position["interviews"]
    assert first["duration_minutes"] == 60
    # APP-011: the latest custom interview projects as other_interview;
    # nested flow updates must still preserve the sibling records and durations.
    assert company["current_stage"] == "other_interview"
    updated = _patch(client, owner, company["id"], {"positions": [{
        "id": position["id"],
        "interviews": [{"id": first["id"], "scheduled_at": "2026-10-14T01:00:00Z"}, {"name": "追加面试", "scheduled_at": None}],
    }]})
    assert updated.status_code == 200
    interviews = {item["id"]: item for item in _json(updated)["positions"][0]["interviews"]}
    assert len(interviews) == 3
    assert interviews[second["id"]] == second
    assert interviews[first["id"]]["duration_minutes"] == 60
    assert _json(updated)["current_stage"] == "first_interview"


@pytest.mark.django_db
def test_last_position_cannot_be_deleted_and_company_delete_removes_resources(client, owner):
    response = _create(client, owner, _company_payload())
    assert response.status_code == 201
    company = _json(response)
    position = company["positions"][0]
    deleted = client.delete(_position_url(company["id"], position["id"]), **_headers(owner))
    assert deleted.status_code == 400
    assert _json(deleted)["code"] == "VALIDATION_ERROR"
    assert client.get(f"{APPLICATIONS_URL}{company['id']}/", **_headers(owner)).status_code == 200
    assert client.delete(f"{APPLICATIONS_URL}{company['id']}/", **_headers(owner)).status_code == 204
    assert client.get(f"{APPLICATIONS_URL}{company['id']}/", **_headers(owner)).status_code == 404
    assert client.post(_position_interviews_url(company["id"], position["id"]), {"name": "一面"}, content_type="application/json", **_headers(owner)).status_code == 404


@pytest.mark.django_db
def test_rename_collision_and_foreign_nested_ids_do_not_change_either_company(client, owner):
    first_response = _create(client, owner, _company_payload("Example One"))
    second_response = _create(client, owner, _company_payload("Example Two"))
    assert first_response.status_code == second_response.status_code == 201
    first, second = _json(first_response), _json(second_response)
    collision = _patch(client, owner, first["id"], {"company_name": " example TWO ", "positions": [_position("新增岗位")]})
    assert collision.status_code == 400
    foreign = _patch(client, owner, first["id"], {"company_name": "不应更名", "positions": [{"id": second["positions"][0]["id"], "position_name": "不应修改"}]})
    assert foreign.status_code == 404
    for original in (first, second):
        assert _json(client.get(f"{APPLICATIONS_URL}{original['id']}/", **_headers(owner))) == original


@pytest.mark.django_db
def test_search_status_filter_and_pagination_return_complete_company(client, owner):
    # APP-010 maps the retired offer value to the canonical rejected status.
    response = _create(client, owner, _company_payload("岗位聚合公司", positions=[_position("后端"), _position("专属数据职位", status="rejected")]))
    assert response.status_code == 201
    company = _json(response)
    other_response = _create(client, owner, _company_payload("其他公司"))
    assert other_response.status_code == 201
    for query in ("search=专属数据", "search=聚合", "application_status=rejected"):
        listing = client.get(f"{APPLICATIONS_URL}?{query}&page_size=10", **_headers(owner))
        assert listing.status_code == 200
        page = _json(listing)
        assert page["count"] == 1
        assert page["results"][0]["id"] == company["id"]
        assert len(page["results"][0]["positions"]) == 2
    ordered = client.get(f"{APPLICATIONS_URL}?ordering=created_at&page_size=10", **_headers(owner))
    assert ordered.status_code == 200
    assert [item["id"] for item in _json(ordered)["results"]] == [company["id"], _json(other_response)["id"]]


@pytest.mark.django_db
def test_unauthenticated_nested_crud_and_children_return_401(client):
    for response in (
        client.get(APPLICATIONS_URL),
        client.post(APPLICATIONS_URL, _company_payload(), content_type="application/json"),
        client.get(f"{APPLICATIONS_URL}1/"),
        client.patch(f"{APPLICATIONS_URL}1/", {"company_name": "x"}, content_type="application/json"),
        client.delete(f"{APPLICATIONS_URL}1/"),
        client.post(_position_interviews_url(1, 1), {"name": "一面"}, content_type="application/json"),
        client.patch(f"{_position_interviews_url(1, 1)}1/", {"name": "一面"}, content_type="application/json"),
        client.delete(f"{_position_interviews_url(1, 1)}1/"),
        client.delete(_position_url(1, 1)),
    ):
        assert response.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_legacy_rows_with_normalized_company_name_migrate_to_one_company_with_all_positions(
    client,
):
    """Seed the public pre-APP-009 schema and inspect only the migrated API."""
    time_fields = {
        "ai_interview_time",
        "written_test_time",
        "first_interview_time",
        "second_interview_time",
        "third_interview_time",
        "hr_interview_time",
    }
    duration_fields = {
        "ai_interview_duration_minutes",
        "written_test_duration_minutes",
        "first_interview_duration_minutes",
        "second_interview_duration_minutes",
        "third_interview_duration_minutes",
        "hr_interview_duration_minutes",
    }

    executor = MigrationExecutor(connection)
    graph = executor.loader.graph
    # Freeze the public migration baseline observed before APP-009 development;
    # a future compatibility model must not make us pick an already-migrated state.
    old_target = ("applications", "0003_jobapplication_stage_durations")
    old_model = executor.loader.project_state([old_target]).apps.get_model("applications", "JobApplication")
    field_names = {field.name for field in old_model._meta.fields}
    assert time_fields <= field_names and duration_fields <= field_names
    latest_targets = graph.leaf_nodes()

    username = f"app009migration{uuid.uuid4().hex[:8]}"
    password = PASSWORD
    user = get_user_model().objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
    )
    earlier_ai = datetime(2026, 10, 5, 1, 0, tzinfo=timezone.utc)
    later_ai = datetime(2026, 10, 6, 1, 0, tzinfo=timezone.utc)
    first_interview = datetime(2026, 10, 7, 2, 0, tzinfo=timezone.utc)
    hr_interview = datetime(2026, 10, 8, 3, 0, tzinfo=timezone.utc)

    try:
        executor.migrate([old_target])
        historical_model = MigrationExecutor(connection).loader.project_state(
            [old_target]
        ).apps.get_model(old_target[0], "JobApplication")
        historical_model.objects.create(
            user_id=user.pk,
            company_name="  Migration Tech  ",
            position_name="后端开发",
            application_status="in_progress",
            notes="迁移保留后端备注",
            application_url="https://example.com/backend",
            ai_interview_time=earlier_ai,
            ai_interview_duration_minutes=37,
            written_test_time=None,
            written_test_duration_minutes=None,
            first_interview_time=first_interview,
            first_interview_duration_minutes=51,
            second_interview_time=None,
            second_interview_duration_minutes=None,
            third_interview_time=None,
            third_interview_duration_minutes=None,
            hr_interview_time=None,
            hr_interview_duration_minutes=None,
        )
        historical_model.objects.create(
            user_id=user.pk,
            company_name="migration TECH",
            position_name="数据工程师",
            application_status="applied",
            notes="迁移保留数据备注",
            application_url="https://example.com/data",
            ai_interview_time=later_ai,
            ai_interview_duration_minutes=42,
            written_test_time=None,
            written_test_duration_minutes=None,
            first_interview_time=None,
            first_interview_duration_minutes=None,
            second_interview_time=None,
            second_interview_duration_minutes=None,
            third_interview_time=None,
            third_interview_duration_minutes=None,
            hr_interview_time=hr_interview,
            hr_interview_duration_minutes=63,
        )

        MigrationExecutor(connection).migrate(latest_targets)
        logged_in = client.post(
            LOGIN_URL,
            {"username": username, "password": password},
            content_type="application/json",
        )
        assert logged_in.status_code == 200
        session = {"access": logged_in.json()["access"]}
        listing = client.get(APPLICATIONS_URL, **_headers(session))
        assert listing.status_code == 200
        page = _json(listing)
        assert page["count"] == 1
        company = page["results"][0]
        assert company["company_name"].strip().lower() == "migration tech"
        positions = {item["position_name"]: item for item in company["positions"]}
        assert set(positions) == {"后端开发", "数据工程师"}
        stages = {item["type"]: item for item in company["shared_stages"]}
        assert stages["ai_interview"]["scheduled_at"] is not None
        assert stages["ai_interview"]["scheduled_at"].startswith("2026-10-05T01:00:00")
        assert stages["ai_interview"]["duration_minutes"] == 37
        assert stages["assessment"]["scheduled_at"] is None
        assert stages["written_test"]["scheduled_at"] is None
        assert len(positions["后端开发"]["interviews"]) == 1
        assert positions["后端开发"]["interviews"][0]["name"] == "一面"
        assert positions["后端开发"]["interviews"][0]["scheduled_at"].startswith("2026-10-07T02:00:00")
        assert positions["后端开发"]["interviews"][0]["duration_minutes"] == 51
        assert positions["后端开发"]["notes"] == "迁移保留后端备注"
        assert positions["后端开发"]["application_url"] == "https://example.com/backend"
        assert len(positions["数据工程师"]["interviews"]) == 1
        assert positions["数据工程师"]["interviews"][0]["name"] == "HR 面"
        assert positions["数据工程师"]["interviews"][0]["scheduled_at"].startswith("2026-10-08T03:00:00")
        assert positions["数据工程师"]["interviews"][0]["duration_minutes"] == 63
        assert positions["数据工程师"]["notes"] == "迁移保留数据备注"
        assert positions["数据工程师"]["application_url"] == "https://example.com/data"
    finally:
        MigrationExecutor(connection).migrate(latest_targets)
