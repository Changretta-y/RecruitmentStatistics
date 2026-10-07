"""Black-box tests for the CAL-002 calendar date-range API contract."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from django.test import Client


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
CALENDAR_URL = "/api/v1/calendar/events/"
PASSWORD = "StrongPass_123"
STAGES = (
    ("ai_interview_time", "ai_interview_duration_minutes", "ai_interview"),
    ("written_test_time", "written_test_duration_minutes", "written_test"),
    ("first_interview_time", "first_interview_duration_minutes", "first_interview"),
    ("second_interview_time", "second_interview_duration_minutes", "second_interview"),
    ("third_interview_time", "third_interview_duration_minutes", "third_interview"),
    ("hr_interview_time", "hr_interview_duration_minutes", "hr_interview"),
)


@pytest.fixture
def client():
    return Client()


def _register(client, prefix: str):
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
    return _login(client, _register(client, "cal002owner"))


@pytest.fixture
def other_user(client):
    return _login(client, _register(client, "cal002other"))


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _application_payload(**overrides):
    payload = {
        "company_name": "日历测试科技",
        "position_name": "后端工程师",
        # APP-010 canonical status; calendar tests exercise scheduled events, not legacy status aliases.
        "application_status": "assessment",
        "application_time": "2026-08-01T09:00:00+08:00",
        "ai_interview_time": None,
        "written_test_time": None,
        "first_interview_time": None,
        "second_interview_time": None,
        "third_interview_time": None,
        "hr_interview_time": None,
        "notes": "CAL-002 black-box test",
    }
    payload.update(overrides)
    return payload


def _create_application(client, session, **overrides):
    response = client.post(
        APPLICATIONS_URL,
        _application_payload(**overrides),
        content_type="application/json",
        **_headers(session),
    )
    assert response.status_code == 201, response.content
    return _json(response)


def _event_query(client, session, start="2026-09-01", end="2026-09-02"):
    return client.get(
        CALENDAR_URL,
        {"start": start, "end": end},
        **_headers(session),
    )


def _event(response):
    body = _json(response)
    assert response.status_code == 200
    assert body["timezone"] == "Asia/Shanghai"
    return body


def _at(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@pytest.mark.django_db
def test_date_window_is_left_closed_right_open_and_includes_crossing_events(client, owner):
    crossing_id = _create_application(
        client,
        owner,
        company_name="跨入范围",
        ai_interview_time="2026-08-31T23:30:00+08:00",
        ai_interview_duration_minutes=120,
    )["id"]
    in_range_id = _create_application(
        client,
        owner,
        company_name="范围内",
        written_test_time="2026-09-01T10:00:00+08:00",
        written_test_duration_minutes=45,
    )["id"]
    ends_at_window_end_id = _create_application(
        client,
        owner,
        company_name="恰好在次日午夜结束",
        first_interview_time="2026-09-01T23:30:00+08:00",
        first_interview_duration_minutes=30,
    )["id"]
    _create_application(
        client,
        owner,
        company_name="午夜前结束",
        first_interview_time="2026-08-31T23:00:00+08:00",
        first_interview_duration_minutes=60,
    )
    midnight_start_id = _create_application(
        client,
        owner,
        company_name="恰好在结束边界开始",
        hr_interview_time="2026-09-02T00:00:00+08:00",
        hr_interview_duration_minutes=60,
    )["id"]

    response = _event_query(client, owner, "2026-09-01", "2026-09-02")

    assert response.status_code == 200
    body = _event(response)
    assert body["start"] == "2026-09-01"
    assert body["end"] == "2026-09-02"
    assert {event["application_id"] for event in body["events"]} == {
        crossing_id,
        in_range_id,
        ends_at_window_end_id,
    }
    events_by_id = {event["application_id"]: event for event in body["events"]}
    crossing = events_by_id[crossing_id]
    inside = events_by_id[in_range_id]
    ending_at_midnight = events_by_id[ends_at_window_end_id]
    assert crossing["stage"] == "ai_interview"
    assert crossing["company_name"] == "跨入范围"
    assert crossing["position_name"] == "后端工程师"
    assert crossing["duration_minutes"] == 120
    assert _at(crossing["start_at"]) == datetime(2026, 8, 31, 15, 30, tzinfo=timezone.utc)
    assert _at(crossing["end_at"]) == datetime(2026, 8, 31, 17, 30, tzinfo=timezone.utc)
    assert inside["stage"] == "written_test"
    assert inside["duration_minutes"] == 45
    assert _at(inside["end_at"]) - _at(inside["start_at"]) == timedelta(minutes=45)
    assert ending_at_midnight["stage"] == "first_interview"
    assert _at(ending_at_midnight["end_at"]) == datetime(
        2026, 9, 1, 16, 0, tzinfo=timezone.utc
    )

    next_day = _event_query(client, owner, "2026-09-02", "2026-09-03")
    assert next_day.status_code == 200
    next_day_events = _event(next_day)["events"]
    assert [event["application_id"] for event in next_day_events] == [midnight_start_id]


@pytest.mark.django_db
def test_six_stage_events_have_public_fields_and_stable_order(client, owner):
    overrides = {
        time_field: "2026-09-10T09:00:00+08:00"
        for time_field, _, _ in STAGES
    }
    overrides.update(
        {
            duration_field: index + 30
            for index, (_, duration_field, _) in enumerate(STAGES)
        }
    )
    first = _create_application(client, owner, company_name="同投递全部阶段", **overrides)
    second_id = _create_application(
        client,
        owner,
        company_name="同刻第二投递",
        first_interview_time="2026-09-10T09:00:00+08:00",
        first_interview_duration_minutes=75,
    )["id"]
    earlier_id = _create_application(
        client,
        owner,
        company_name="开始更早但 ID 更大",
        ai_interview_time="2026-09-10T08:00:00+08:00",
        ai_interview_duration_minutes=30,
    )["id"]

    response = _event_query(client, owner, "2026-09-10", "2026-09-11")

    assert response.status_code == 200
    events = _event(response)["events"]
    assert len(events) == 8
    assert all(
        {"application_id", "company_name", "position_name", "stage", "start_at", "end_at", "duration_minutes"}
        <= set(event)
        for event in events
    )
    assert events[0]["application_id"] == earlier_id
    assert [event["stage"] for event in events[1:7]] == [stage for _, _, stage in STAGES]
    assert [event["application_id"] for event in events[1:7]] == [first["id"]] * 6
    assert events[7]["application_id"] == second_id
    assert [event["duration_minutes"] for event in events[1:7]] == [
        index + 30 for index in range(6)
    ]
    assert all(
        _at(event["end_at"]) - _at(event["start_at"])
        == timedelta(minutes=event["duration_minutes"])
        for event in events
    )


@pytest.mark.django_db
def test_more_than_one_hundred_events_are_returned_without_application_pagination(client, owner):
    expected_ids = {
        _create_application(
            client,
            owner,
            company_name=f"批量安排{i:03d}",
            ai_interview_time=f"2026-09-{1 + (i % 28):02d}T09:00:00+08:00",
            ai_interview_duration_minutes=30,
        )["id"]
        for i in range(101)
    }

    response = _event_query(client, owner, "2026-09-01", "2026-09-29")

    assert response.status_code == 200
    events = _event(response)["events"]
    assert len(events) == 101
    assert {event["application_id"] for event in events} == expected_ids


@pytest.mark.django_db
def test_empty_range_returns_an_empty_events_array(client, owner):
    response = _event_query(client, owner)

    assert response.status_code == 200
    assert _event(response)["events"] == []


@pytest.mark.django_db
def test_calendar_events_are_isolated_between_users(client, owner, other_user):
    own_id = _create_application(
        client,
        owner,
        company_name="仅本人可见",
        hr_interview_time="2026-09-15T09:00:00+08:00",
        hr_interview_duration_minutes=60,
    )["id"]
    other_id = _create_application(
        client,
        other_user,
        company_name="其他用户秘密公司",
        written_test_time="2026-09-15T10:00:00+08:00",
        written_test_duration_minutes=60,
    )["id"]

    owner_body = _event_query(client, owner, "2026-09-15", "2026-09-16")
    other_body = _event_query(client, other_user, "2026-09-15", "2026-09-16")

    assert owner_body.status_code == 200
    assert other_body.status_code == 200
    owner_events = _event(owner_body)["events"]
    other_events = _event(other_body)["events"]
    assert [event["application_id"] for event in owner_events] == [own_id]
    assert "其他用户秘密公司" not in str(owner_events)
    assert [event["application_id"] for event in other_events] == [other_id]
    assert "仅本人可见" not in str(other_events)


@pytest.mark.django_db
def test_terminal_application_keeps_scheduled_stage_and_clear_or_delete_removes_it(client, owner):
    terminal = _create_application(
        client,
        owner,
        company_name="已拿 Offer 仍有安排",
        # APP-010 maps the retired offer alias to the canonical terminal status.
        application_status="rejected",
        second_interview_time="2026-09-20T13:00:00+08:00",
        second_interview_duration_minutes=90,
    )
    removable = _create_application(
        client,
        owner,
        company_name="稍后删除",
        hr_interview_time="2026-09-20T15:00:00+08:00",
        hr_interview_duration_minutes=60,
    )
    headers = {"content_type": "application/json", **_headers(owner)}

    before = _event_query(client, owner, "2026-09-20", "2026-09-21")
    assert before.status_code == 200
    assert {event["application_id"] for event in _event(before)["events"]} == {
        terminal["id"],
        removable["id"],
    }

    clear = client.patch(
        f"{APPLICATIONS_URL}{terminal['id']}/",
        {"second_interview_time": None},
        **headers,
    )
    assert clear.status_code == 200
    delete = client.delete(f"{APPLICATIONS_URL}{removable['id']}/", **_headers(owner))
    assert delete.status_code == 204

    after = _event_query(client, owner, "2026-09-20", "2026-09-21")
    assert after.status_code == 200
    assert _event(after)["events"] == []


@pytest.mark.django_db
def test_unauthenticated_calendar_query_returns_401(client):
    response = client.get(CALENDAR_URL, {"start": "2026-09-01", "end": "2026-09-02"})

    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("params", "marked_parameter"),
    [
        ({}, "start"),
        ({"end": "2026-09-02"}, "start"),
        ({"start": "2026-09-01"}, "end"),
        ({"start": "not-a-date", "end": "2026-09-02"}, "start"),
        ({"start": "2026-09-01", "end": "2026-02-30"}, "end"),
        ({"start": "2026-09-02", "end": "2026-09-02"}, "start"),
        ({"start": "2026-09-03", "end": "2026-09-02"}, "end"),
        ({"start": "2026-08-01", "end": "2026-09-13"}, "end"),
    ],
)
def test_missing_malformed_reversed_or_overlong_date_ranges_return_field_validation_error(
    client, owner, params, marked_parameter
):
    response = client.get(CALENDAR_URL, params, **_headers(owner))

    assert response.status_code == 400
    body = _json(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert marked_parameter in body["details"]
