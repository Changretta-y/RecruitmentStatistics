"""Black-box tests for APP-008 stage duration API behavior."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
PASSWORD = "StrongPass_123"

STAGES = (
    ("ai_interview_time", "ai_interview_duration_minutes"),
    ("written_test_time", "written_test_duration_minutes"),
    ("first_interview_time", "first_interview_duration_minutes"),
    ("second_interview_time", "second_interview_duration_minutes"),
    ("third_interview_time", "third_interview_duration_minutes"),
    ("hr_interview_time", "hr_interview_duration_minutes"),
)
DURATION_FIELDS = {duration for _, duration in STAGES}
STAGE_TIMES = {time_field for time_field, _ in STAGES}


@pytest.fixture
def client():
    return Client()


def _register(client, prefix="app008"):
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
    return {"access": response.json()["access"]}


@pytest.fixture
def owner(client):
    return _login(client, _register(client))


@pytest.fixture
def other_user(client):
    return _login(client, _register(client, "other008"))


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _payload(**overrides):
    payload = {
        "company_name": "时长契约科技",
        "position_name": "后端工程师",
        "application_status": "in_progress",
        "ai_interview_time": "2026-10-05T09:00:00+08:00",
        "written_test_time": "2026-10-05T10:00:00+08:00",
        "first_interview_time": "2026-10-05T11:00:00+08:00",
        "second_interview_time": "2026-10-05T13:00:00+08:00",
        "third_interview_time": "2026-10-05T14:00:00+08:00",
        "hr_interview_time": "2026-10-05T15:00:00+08:00",
        "notes": "APP-008 black-box test",
    }
    payload.update(overrides)
    return payload


def _create(client, session, payload=None):
    response = client.post(
        APPLICATIONS_URL,
        payload if payload is not None else _payload(),
        content_type="application/json",
        **_headers(session),
    )
    return response


def _patch(client, session, application_id, payload):
    return client.patch(
        f"{APPLICATIONS_URL}{application_id}/",
        payload,
        content_type="application/json",
        **_headers(session),
    )


def _assert_durations(record, expected):
    assert DURATION_FIELDS <= set(record)
    for _, field in STAGES:
        assert record[field] == expected[field]


@pytest.mark.django_db
def test_create_detail_and_list_round_trip_six_independent_durations(client, owner):
    durations = {duration: minutes for (_, duration), minutes in zip(STAGES, (31, 42, 53, 64, 75, 86))}

    created_response = _create(client, owner, _payload(**durations))

    assert created_response.status_code == 201
    created = _json(created_response)
    _assert_durations(created, durations)
    assert len({created[field] for field in DURATION_FIELDS}) == 6

    detail_response = client.get(
        f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner)
    )
    assert detail_response.status_code == 200
    _assert_durations(_json(detail_response), durations)

    list_response = client.get(APPLICATIONS_URL, **_headers(owner))
    assert list_response.status_code == 200
    records = _json(list_response)["results"]
    assert len(records) == 1
    _assert_durations(records[0], durations)


@pytest.mark.django_db
def test_create_with_stage_times_only_defaults_each_missing_duration_to_sixty(
    client, owner
):
    response = _create(client, owner, _payload())

    assert response.status_code == 201
    body = _json(response)
    _assert_durations(body, {field: 60 for field in DURATION_FIELDS})


@pytest.mark.django_db
@pytest.mark.parametrize(("time_field", "duration_field"), STAGES)
def test_patch_duration_and_start_time_rules_are_independent_and_linked(
    client, owner, time_field, duration_field
):
    created_response = _create(client, owner, _payload(**{duration_field: 37}))
    assert created_response.status_code == 201
    created = _json(created_response)

    duration_response = _patch(
        client, owner, created["id"], {duration_field: 91}
    )
    assert duration_response.status_code == 200
    duration_body = _json(duration_response)
    assert duration_body[duration_field] == 91
    for _, other_duration in STAGES:
        if other_duration != duration_field:
            assert duration_body[other_duration] == created[other_duration]
    assert duration_body[time_field] == created[time_field]

    changed_time_response = _patch(
        client,
        owner,
        created["id"],
        {time_field: "2026-10-06T09:30:00+08:00"},
    )
    assert changed_time_response.status_code == 200
    changed_time = _json(changed_time_response)
    assert changed_time[duration_field] == 91

    cleared_response = _patch(client, owner, created["id"], {time_field: None})
    assert cleared_response.status_code == 200
    cleared = _json(cleared_response)
    assert cleared[time_field] is None
    assert cleared[duration_field] is None


@pytest.mark.django_db
@pytest.mark.parametrize(("time_field", "duration_field"), STAGES)
def test_setting_new_stage_time_without_duration_defaults_to_sixty(
    client, owner, time_field, duration_field
):
    created_response = _create(client, owner, _payload(**{time_field: None}))
    assert created_response.status_code == 201
    created = _json(created_response)

    response = _patch(
        client,
        owner,
        created["id"],
        {time_field: "2026-10-06T09:30:00+08:00"},
    )

    assert response.status_code == 200
    assert _json(response)[duration_field] == 60


@pytest.mark.django_db
@pytest.mark.parametrize(("time_field", "duration_field"), STAGES)
@pytest.mark.parametrize("invalid_value", [None, 0, -1, 1441, 1.5, "30"])
def test_invalid_duration_values_return_field_validation_error_without_write(
    client, owner, time_field, duration_field, invalid_value
):
    created_response = _create(client, owner, _payload(**{duration_field: 45}))
    assert created_response.status_code == 201
    created = _json(created_response)

    response = _patch(
        client, owner, created["id"], {duration_field: invalid_value}
    )

    assert response.status_code == 400
    error = _json(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert duration_field in error["details"]
    unchanged = _json(
        client.get(f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner))
    )
    assert unchanged[duration_field] == 45
    assert unchanged[time_field] == created[time_field]


@pytest.mark.django_db
@pytest.mark.parametrize(("time_field", "duration_field"), STAGES)
def test_duration_cannot_be_set_without_start_time(client, owner, time_field, duration_field):
    created_response = _create(
        client,
        owner,
        _payload(**{time_field: None, duration_field: None}),
    )
    assert created_response.status_code == 201
    created = _json(created_response)

    response = _patch(client, owner, created["id"], {duration_field: 30})

    assert response.status_code == 400
    error = _json(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert duration_field in error["details"]
    unchanged = _json(
        client.get(f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner))
    )
    assert unchanged[duration_field] is None
    assert unchanged[time_field] is None


@pytest.mark.django_db
@pytest.mark.parametrize(("time_field", "duration_field"), STAGES)
def test_create_rejects_non_null_duration_without_start_time(
    client, owner, time_field, duration_field
):
    response = _create(
        client,
        owner,
        _payload(**{time_field: None, duration_field: 30}),
    )

    assert response.status_code == 400
    error = _json(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert duration_field in error["details"]


@pytest.mark.django_db
@pytest.mark.parametrize(("time_field", "duration_field"), STAGES)
def test_clearing_start_time_and_supplying_duration_is_rejected(client, owner, time_field, duration_field):
    created_response = _create(client, owner, _payload(**{duration_field: 45}))
    assert created_response.status_code == 201
    created = _json(created_response)

    response = _patch(
        client,
        owner,
        created["id"],
        {time_field: None, duration_field: 45},
    )

    assert response.status_code == 400
    error = _json(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert {time_field, duration_field} & set(error["details"])
    unchanged = _json(
        client.get(f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner))
    )
    assert unchanged[time_field] == created[time_field]
    assert unchanged[duration_field] == 45


@pytest.mark.django_db
def test_duration_fields_remain_owner_scoped_for_list_detail_and_patch(
    client, owner, other_user
):
    created_response = _create(
        client,
        owner,
        _payload(ai_interview_duration_minutes=83),
    )
    assert created_response.status_code == 201
    created = _json(created_response)

    other_list = client.get(APPLICATIONS_URL, **_headers(other_user))
    other_detail = client.get(
        f"{APPLICATIONS_URL}{created['id']}/", **_headers(other_user)
    )
    other_patch = _patch(
        client,
        other_user,
        created["id"],
        {"ai_interview_duration_minutes": 99},
    )

    assert other_list.status_code == 200
    assert created["id"] not in {row["id"] for row in _json(other_list)["results"]}
    assert other_detail.status_code == 404
    assert other_patch.status_code == 404
    owner_detail = client.get(
        f"{APPLICATIONS_URL}{created['id']}/", **_headers(owner)
    )
    assert owner_detail.status_code == 200
    assert _json(owner_detail)["ai_interview_duration_minutes"] == 83


@pytest.mark.django_db
def test_unauthenticated_create_with_durations_returns_401(client):
    response = client.post(
        APPLICATIONS_URL,
        _payload(ai_interview_duration_minutes=45),
        content_type="application/json",
    )

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_forward_migration_maps_legacy_stage_times_to_sixty_or_null(client):
    """Seed the public pre-duration schema, migrate forward, then observe via API."""
    current_model = next(
        model for model in apps.get_models() if model.__name__ == "JobApplication"
    )
    app_label = current_model._meta.app_label
    time_names = {time_field for time_field, _ in STAGES}
    duration_names = {duration_field for _, duration_field in STAGES}

    executor = MigrationExecutor(connection)
    graph = executor.loader.graph
    pre_duration_nodes = []
    for node in graph.nodes:
        if node[0] != app_label:
            continue
        historical_apps = graph.make_state([node]).apps
        try:
            historical_model = historical_apps.get_model(app_label, "JobApplication")
        except LookupError:
            continue
        historical_fields = {field.name for field in historical_model._meta.fields}
        if time_names <= historical_fields and duration_names.isdisjoint(historical_fields):
            pre_duration_nodes.append(node)

    assert pre_duration_nodes, "找不到包含六个旧阶段时间字段且未含时长字段的历史迁移状态"
    pre_duration_target = max(
        pre_duration_nodes,
        key=lambda node: len(graph.forwards_plan(node)),
    )
    latest_targets = graph.leaf_nodes()

    username = f"app008migration{uuid.uuid4().hex[:8]}"
    password = PASSWORD
    user = get_user_model().objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
    )

    try:
        executor.migrate([pre_duration_target])
        historical_model = MigrationExecutor(connection).loader.project_state(
            [pre_duration_target]
        ).apps.get_model(app_label, "JobApplication")
        historical_model.objects.create(
            user_id=user.pk,
            company_name="历史安排科技",
            position_name="算法工程师",
            application_status="in_progress",
            ai_interview_time=datetime(2026, 10, 5, 1, 0, tzinfo=timezone.utc),
            written_test_time=None,
            first_interview_time=datetime(2026, 10, 5, 3, 0, tzinfo=timezone.utc),
            second_interview_time=None,
            third_interview_time=None,
            hr_interview_time=datetime(2026, 10, 5, 7, 0, tzinfo=timezone.utc),
        )
        application_id = historical_model.objects.get(
            user_id=user.pk, company_name="历史安排科技"
        ).pk

        MigrationExecutor(connection).migrate(latest_targets)

        login = client.post(
            LOGIN_URL,
            {"username": username, "password": password},
            content_type="application/json",
        )
        assert login.status_code == 200
        session = {"access": login.json()["access"]}
        detail = client.get(
            f"{APPLICATIONS_URL}{application_id}/", **_headers(session)
        )

        assert detail.status_code == 200
        body = _json(detail)
        expected = {
            "ai_interview_duration_minutes": 60,
            "written_test_duration_minutes": None,
            "first_interview_duration_minutes": 60,
            "second_interview_duration_minutes": None,
            "third_interview_duration_minutes": None,
            "hr_interview_duration_minutes": 60,
        }
        _assert_durations(body, expected)
    finally:
        MigrationExecutor(connection).migrate(latest_targets)
