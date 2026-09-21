"""Black-box tests for APP-002 application creation API."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from django.apps import apps
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
RESPONSE_FIELDS = {
    "id",
    "user",
    "company_name",
    "position_name",
    "application_status",
    "current_stage",
    "application_time",
    *STAGE_FIELDS,
    "notes",
    "created_at",
    "updated_at",
}


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def application_model():
    for model in apps.get_models():
        if model.__name__ == "JobApplication":
            return model
    pytest.fail("公开 Django app registry 中未注册 JobApplication 模型")


def _register(client, email_prefix: str = "app002"):
    username = f"{email_prefix}{uuid.uuid4().hex[:12]}"
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


@pytest.fixture
def auth_session(client):
    credentials = _register(client)
    login = client.post(LOGIN_URL, credentials, content_type="application/json")
    assert login.status_code == 200
    user = get_user_model().objects.get(username=credentials["username"])
    return {"access": login.json()["access"], "user": user}


def _payload(**overrides):
    payload = {
        "company_name": "示例科技",
        "position_name": "后端开发工程师",
        "application_time": "2026-09-20T10:00:00+08:00",
        "ai_interview_time": None,
        "written_test_time": None,
        "first_interview_time": None,
        "second_interview_time": None,
        "third_interview_time": None,
        "hr_interview_time": None,
        "notes": "官网投递",
    }
    payload.update(overrides)
    return payload


def _json_response(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _application_queryset(application_model):
    return application_model.objects.all()


@pytest.mark.django_db
def test_authenticated_create_returns_complete_record_and_persists_owner(
    client, auth_session, application_model
):
    response = client.post(
        APPLICATIONS_URL,
        _payload(),
        HTTP_AUTHORIZATION=f"Bearer {auth_session['access']}",
        content_type="application/json",
    )

    assert response.status_code == 201
    body = _json_response(response)
    assert RESPONSE_FIELDS <= set(body)
    assert body["user"] == auth_session["user"].id
    assert body["company_name"] == "示例科技"
    assert body["position_name"] == "后端开发工程师"
    assert body["application_status"] == "applied"
    assert body["current_stage"] == "applied"
    assert body["application_time"]
    assert body["notes"] == "官网投递"
    assert "password" not in body
    assert "access" not in body
    assert "refresh" not in body

    stored = application_model.objects.get(pk=body["id"])
    assert stored.user_id == auth_session["user"].id
    assert stored.application_time == datetime(2026, 9, 20, 2, 0, tzinfo=timezone.utc)


@pytest.mark.django_db
def test_create_defaults_status_notes_and_all_stage_times_to_null(
    client, auth_session, application_model
):
    response = client.post(
        APPLICATIONS_URL,
        {"company_name": "默认科技", "position_name": "测试工程师"},
        HTTP_AUTHORIZATION=f"Bearer {auth_session['access']}",
        content_type="application/json",
    )

    assert response.status_code == 201
    body = _json_response(response)
    assert body["application_status"] == "applied"
    assert body["notes"] == ""
    assert body["application_time"] is None
    assert all(body[field] is None for field in STAGE_FIELDS)
    assert application_model.objects.filter(
        pk=body["id"], user_id=auth_session["user"].id
    ).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "fields"),
    [
        ({"position_name": "后端开发工程师"}, {"company_name"}),
        ({"company_name": "示例科技"}, {"position_name"}),
        ({"company_name": "   ", "position_name": "后端开发工程师"}, {"company_name"}),
        ({"company_name": "示例科技", "position_name": "   "}, {"position_name"}),
        ({"company_name": "示例科技", "position_name": "后端开发工程师", "application_status": "unknown"}, {"application_status"}),
        ({"company_name": "示例科技", "position_name": "后端开发工程师", "application_time": "not-an-iso-time"}, {"application_time"}),
    ],
)
def test_invalid_application_fields_return_structured_400(
    client, auth_session, application_model, payload, fields
):
    before = application_model.objects.filter(user_id=auth_session["user"].id).count()
    response = client.post(
        APPLICATIONS_URL,
        payload,
        HTTP_AUTHORIZATION=f"Bearer {auth_session['access']}",
        content_type="application/json",
    )

    assert response.status_code == 400
    body = _json_response(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert fields <= set(body["details"])
    assert application_model.objects.filter(user_id=auth_session["user"].id).count() == before


@pytest.mark.django_db
def test_forged_user_is_ignored_or_rejected_without_wrong_ownership(
    client, auth_session, application_model
):
    other_credentials = _register(client, "other002")
    other_user = get_user_model().objects.get(username=other_credentials["username"])
    before = application_model.objects.count()

    response = client.post(
        APPLICATIONS_URL,
        _payload(user=other_user.id),
        HTTP_AUTHORIZATION=f"Bearer {auth_session['access']}",
        content_type="application/json",
    )

    assert response.status_code in {201, 400}
    if response.status_code == 201:
        body = _json_response(response)
        assert body["user"] == auth_session["user"].id
        created = application_model.objects.get(pk=body["id"])
        assert created.user_id == auth_session["user"].id
        assert not application_model.objects.filter(
            pk=body["id"], user_id=other_user.id
        ).exists()
    else:
        assert _json_response(response)["code"] == "VALIDATION_ERROR"
        assert application_model.objects.count() == before


@pytest.mark.django_db
def test_unauthenticated_create_returns_401_and_does_not_persist(
    client, application_model
):
    before = application_model.objects.count()
    response = client.post(
        APPLICATIONS_URL,
        _payload(),
        content_type="application/json",
    )

    assert response.status_code == 401
    assert application_model.objects.count() == before
