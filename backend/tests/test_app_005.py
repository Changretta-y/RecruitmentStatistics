"""Black-box tests for APP-005 application filtering and ordering."""

from __future__ import annotations

from datetime import datetime
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
ORDERING_FIELDS = ("created_at", "updated_at", "application_time", *STAGE_FIELDS)
STATUSES = ("applied", "in_progress", "offer", "rejected", "withdrawn")


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


def _auth_headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _record_payload(**overrides):
    payload = {
        "company_name": "普通科技",
        "position_name": "普通岗位",
        "application_status": "applied",
        "application_time": None,
        "ai_interview_time": None,
        "written_test_time": None,
        "first_interview_time": None,
        "second_interview_time": None,
        "third_interview_time": None,
        "hr_interview_time": None,
        "notes": "APP-005 test data",
    }
    payload.update(overrides)
    return payload


def _create(client, session, **overrides):
    response = client.post(
        APPLICATIONS_URL,
        _record_payload(**overrides),
        content_type="application/json",
        **_auth_headers(session),
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def filter_dataset(client):
    owner = _login(client, _register(client, "app005owner"))
    other = _login(client, _register(client, "app005other"))

    owner_specs = [
        {
            "key": "alpha",
            "company_name": "Needle Systems",
            "position_name": "后端工程师",
            "application_status": "applied",
            "application_time": "2026-01-10T09:00:00+08:00",
            "ai_interview_time": "2026-01-11T09:00:00+08:00",
        },
        {
            "key": "beta",
            "company_name": "普通实验室",
            "position_name": "Needle Platform Engineer",
            "application_status": "in_progress",
            "application_time": "2026-02-10T09:00:00+08:00",
            "written_test_time": "2026-02-11T09:00:00+08:00",
        },
        {
            "key": "gamma",
            "company_name": "三月科技",
            "position_name": "产品经理",
            "application_status": "offer",
            "application_time": "2026-03-10T09:00:00+08:00",
            "first_interview_time": "2026-03-11T09:00:00+08:00",
        },
        {
            "key": "delta",
            "company_name": "四月科技",
            "position_name": "测试工程师",
            "application_status": "rejected",
            "application_time": "2026-04-10T09:00:00+08:00",
            "second_interview_time": "2026-04-11T09:00:00+08:00",
        },
        {
            "key": "epsilon",
            "company_name": "五月科技",
            "position_name": "运营专员",
            "application_status": "withdrawn",
            "application_time": "2026-05-10T09:00:00+08:00",
            "third_interview_time": "2026-05-11T09:00:00+08:00",
        },
        {
            "key": "zeta",
            "company_name": "六月科技",
            "position_name": "算法工程师",
            "application_status": "applied",
            "application_time": "2026-06-10T09:00:00+08:00",
            "hr_interview_time": "2026-06-11T09:00:00+08:00",
        },
        {
            "key": "eta",
            "company_name": "无时间科技",
            "position_name": "数据工程师",
            "application_status": "in_progress",
        },
        {
            "key": "theta",
            "company_name": "空阶段科技",
            "position_name": "架构师",
            "application_status": "applied",
            "application_time": "2026-07-10T09:00:00+08:00",
        },
    ]
    records = {
        spec["key"]: _create(client, owner, **{k: v for k, v in spec.items() if k != "key"})
        for spec in owner_specs
    }
    other_record = _create(
        client,
        other,
        company_name="Needle Systems",
        position_name="他人岗位",
        application_status="applied",
        application_time="2026-08-10T09:00:00+08:00",
    )
    return {"owner": owner, "other": other, "records": records, "other_record": other_record}


def _list(client, owner, query=""):
    return client.get(f"{APPLICATIONS_URL}{query}", **_auth_headers(owner))


def _result_ids(body):
    return [item["id"] for item in body["results"]]


@pytest.mark.django_db
def test_search_matches_company_or_position_and_keeps_user_isolation(
    client, filter_dataset
):
    owner = filter_dataset["owner"]
    records = filter_dataset["records"]
    other_record = filter_dataset["other_record"]

    company_search = _json(_list(client, owner, "?search=Needle"))
    position_search = _json(_list(client, owner, "?search=Platform"))

    assert {item["id"] for item in company_search["results"]} == {
        records["alpha"]["id"],
        records["beta"]["id"],
    }
    assert other_record["id"] not in _result_ids(company_search)
    assert {item["id"] for item in position_search["results"]} == {records["beta"]["id"]}


@pytest.mark.django_db
@pytest.mark.parametrize("status", STATUSES)
def test_each_application_status_filter_returns_only_matching_status(
    client, filter_dataset, status
):
    owner = filter_dataset["owner"]
    records = filter_dataset["records"]

    response = _list(client, owner, f"?application_status={status}")

    assert response.status_code == 200
    body = _json(response)
    expected_keys = {
        "applied": ("alpha", "zeta", "theta"),
        "in_progress": ("beta", "eta"),
        "offer": ("gamma",),
        "rejected": ("delta",),
        "withdrawn": ("epsilon",),
    }[status]
    assert body["count"] == len(expected_keys)
    assert set(_result_ids(body)) == {records[key]["id"] for key in expected_keys}
    assert all(item["application_status"] == status for item in body["results"])


@pytest.mark.django_db
@pytest.mark.parametrize("stage", STAGE_FIELDS)
def test_each_stage_filter_separates_filled_from_unfilled(client, filter_dataset, stage):
    owner = filter_dataset["owner"]
    records = filter_dataset["records"]
    filled_key = {
        "ai_interview_time": "alpha",
        "written_test_time": "beta",
        "first_interview_time": "gamma",
        "second_interview_time": "delta",
        "third_interview_time": "epsilon",
        "hr_interview_time": "zeta",
    }[stage]

    response = _list(client, owner, f"?stage={stage.removesuffix('_time')}")

    assert response.status_code == 200
    body = _json(response)
    assert body["count"] == 1
    assert _result_ids(body) == [records[filled_key]["id"]]
    assert body["results"][0][stage] is not None
    assert all(item[stage] is not None for item in body["results"])


@pytest.mark.django_db
def test_application_time_after_and_before_filter_iso_ranges(client, filter_dataset):
    owner = filter_dataset["owner"]
    records = filter_dataset["records"]

    after = _json(
        _list(client, owner, "?application_time_after=2026-03-01T00:00:00%2B08:00")
    )
    before = _json(
        _list(client, owner, "?application_time_before=2026-03-03T00:00:00%2B08:00")
    )

    assert set(_result_ids(after)) == {
        records[key]["id"] for key in ("gamma", "delta", "epsilon", "zeta", "theta")
    }
    assert set(_result_ids(before)) == {records[key]["id"] for key in ("alpha", "beta")}
    assert records["eta"]["id"] not in _result_ids(after)


@pytest.mark.django_db
def test_all_ordering_whitelist_fields_support_both_directions_and_nulls_last(
    client, filter_dataset
):
    owner = filter_dataset["owner"]

    for field in ORDERING_FIELDS:
        for descending in (False, True):
            prefix = "-" if descending else ""
            response = _list(client, owner, f"?page_size=100&ordering={prefix}{field}")
            assert response.status_code == 200, (field, descending, response.status_code)
            body = _json(response)
            items = body["results"]
            assert body["count"] == len(items)

            non_null = [item for item in items if item[field] is not None]
            nulls = [item for item in items if item[field] is None]
            non_null.sort(
                key=lambda item: datetime.fromisoformat(item[field].replace("Z", "+00:00")),
                reverse=descending,
            )
            assert _result_ids(body) == [item["id"] for item in non_null + nulls], (
                field,
                descending,
            )


@pytest.mark.django_db
def test_default_ordering_is_updated_descending_then_id_descending(client, filter_dataset):
    owner = filter_dataset["owner"]

    first = _json(_list(client, owner, "?page_size=100"))
    second = _json(_list(client, owner, "?page_size=100"))

    assert _result_ids(first) == _result_ids(second)
    assert _result_ids(first) == sorted(_result_ids(first), reverse=True)


@pytest.mark.django_db
def test_combined_filter_ordering_and_pagination_is_applied_together(
    client, filter_dataset
):
    owner = filter_dataset["owner"]
    records = filter_dataset["records"]

    response = _list(
        client,
        owner,
        "?page=1&page_size=10&application_status=applied&search=科技&ordering=-application_time",
    )

    assert response.status_code == 200
    body = _json(response)
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["count"] == 2
    assert set(_result_ids(body)) == {records["zeta"]["id"], records["theta"]["id"]}
    assert _result_ids(body)[0] == records["theta"]["id"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("application_status=unknown", "application_status"),
        ("stage=unknown", "stage"),
        ("application_time_after=not-a-time", "application_time_after"),
        ("ordering=not_allowed", "ordering"),
        ("ordering=current_stage", "ordering"),
    ],
)
def test_invalid_filter_and_ordering_return_uniform_validation_error(
    client, filter_dataset, query, field
):
    owner = filter_dataset["owner"]

    response = _list(client, owner, f"?{query}")

    assert response.status_code == 400
    body = _json(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert field in body["details"]
