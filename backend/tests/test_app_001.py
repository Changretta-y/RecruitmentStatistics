"""Black-box tests for APP-001 JobApplication model and migration contract."""

from __future__ import annotations

import time
from datetime import timedelta

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone


STAGE_FIELDS = (
    ("ai_interview_time", "ai_interview"),
    ("written_test_time", "written_test"),
    ("first_interview_time", "first_interview"),
    ("second_interview_time", "second_interview"),
    ("third_interview_time", "third_interview"),
    ("hr_interview_time", "hr_interview"),
)
TERMINAL_STATUSES = ("offer", "rejected", "withdrawn")


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="app001-user",
        email="app001@example.com",
        password="StrongPass_123",
    )


@pytest.fixture
def job_application_model():
    for model in apps.get_models():
        if model.__name__ == "JobApplication":
            return model
    return None



def _require_model(model):
    assert model is not None, "公开 Django app registry 中未注册 JobApplication 模型"
    return model

def _application(model, user, **overrides):
    values = {
        "user": user,
        "company_name": "示例科技",
        "position_name": "后端开发工程师",
    }
    values.update(overrides)
    return model(**values)


@pytest.mark.django_db
def test_migration_creates_public_job_applications_table(job_application_model):
    job_application_model = _require_model(job_application_model)
    assert job_application_model._meta.db_table == "job_applications"
    assert "job_applications" in connection.introspection.table_names()


@pytest.mark.django_db
def test_defaults_persist_and_all_stage_times_are_nullable(job_application_model, user):
    job_application_model = _require_model(job_application_model)
    application = _application(job_application_model, user)
    application.full_clean()
    application.save()
    application.refresh_from_db()

    assert application.application_status == "applied"
    assert application.notes == ""
    assert all(getattr(application, field) is None for field, _ in STAGE_FIELDS)
    assert application.application_time is None
    assert timezone.is_aware(application.created_at)
    assert timezone.is_aware(application.updated_at)


@pytest.mark.django_db
def test_field_validation_rejects_blank_names_long_names_and_invalid_status(
    job_application_model, user
):
    job_application_model = _require_model(job_application_model)
    for field in ("company_name", "position_name"):
        application = _application(job_application_model, user, **{field: "   "})
        with pytest.raises(ValidationError) as exc_info:
            application.full_clean()
        assert field in exc_info.value.message_dict

    too_long = _application(job_application_model, user, company_name="x" * 201)
    with pytest.raises(ValidationError) as exc_info:
        too_long.full_clean()
    assert "company_name" in exc_info.value.message_dict

    invalid_status = _application(job_application_model, user, application_status="unknown")
    with pytest.raises(ValidationError) as exc_info:
        invalid_status.full_clean()
    assert "application_status" in exc_info.value.message_dict


@pytest.mark.django_db
def test_aware_times_round_trip_and_updated_at_changes(job_application_model, user):
    job_application_model = _require_model(job_application_model)
    event_time = timezone.now().replace(microsecond=123456)
    application = _application(
        job_application_model,
        user,
        application_time=event_time,
        ai_interview_time=event_time + timedelta(hours=1),
    )
    application.save()
    created_at = application.created_at
    updated_at = application.updated_at
    application.refresh_from_db()

    assert timezone.is_aware(application.application_time)
    assert application.application_time == event_time
    assert timezone.is_aware(application.ai_interview_time)
    assert application.created_at == created_at
    assert application.updated_at == updated_at

    time.sleep(0.02)
    application.notes = "已更新"
    application.save()
    assert application.updated_at > updated_at


@pytest.mark.django_db
def test_current_stage_covers_each_stage_and_priority(job_application_model, user):
    job_application_model = _require_model(job_application_model)
    application = _application(job_application_model, user)
    application.save()
    assert application.current_stage == "applied"

    event_time = timezone.now()
    for field, expected_stage in STAGE_FIELDS:
        setattr(application, field, event_time)
        application.save()
        assert application.current_stage == expected_stage

    application.hr_interview_time = None
    application.save()
    assert application.current_stage == "third_interview"
    application.third_interview_time = None
    application.save()
    assert application.current_stage == "second_interview"
    application.second_interview_time = None
    application.save()
    assert application.current_stage == "first_interview"


@pytest.mark.django_db
@pytest.mark.parametrize("status", TERMINAL_STATUSES)
def test_terminal_status_takes_priority_over_derived_stage(
    job_application_model, user, status
):
    job_application_model = _require_model(job_application_model)
    application = _application(
        job_application_model,
        user,
        application_status=status,
        first_interview_time=timezone.now(),
    )
    application.save()

    assert application.current_stage == status


@pytest.mark.django_db
def test_deleting_user_cascades_to_job_applications(job_application_model, user):
    job_application_model = _require_model(job_application_model)
    application = _application(job_application_model, user)
    application.save()
    application_id = application.pk

    user.delete()

    assert not job_application_model.objects.filter(pk=application_id).exists()


@pytest.mark.django_db
def test_required_user_indexes_are_declared(job_application_model):
    job_application_model = _require_model(job_application_model)
    indexed_fields = {tuple(index.fields) for index in job_application_model._meta.indexes}

    assert ("user", "-updated_at") in indexed_fields
    assert ("user", "application_status") in indexed_fields
    assert ("user", "company_name") in indexed_fields
