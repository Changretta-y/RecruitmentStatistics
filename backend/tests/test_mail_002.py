"""Black-box tests for the MAIL-002 daily summary delivery contract."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
import re
import smtplib
import threading
import time as time_module
import uuid
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.core.management import call_command
from django.test import Client, override_settings
from django.utils import timezone


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
APPLICATIONS_URL = "/api/v1/applications/"
SETTINGS_URL = "/api/v1/notification-settings/"
REQUEST_VERIFICATION_URL = f"{SETTINGS_URL}verification/"
VERIFY_URL = f"{SETTINGS_URL}verify/"
PASSWORD = "StrongPass_123"
BEIJING = ZoneInfo("Asia/Shanghai")


class ExplicitRefusalBackend(BaseEmailBackend):
    """A local mail transport which rejects selected messages before acceptance."""

    attempts: Counter[str] = Counter()
    accepted: list = []
    refuse: set[str] = set()
    refuse_once: set[str] = set()

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            recipient = message.to[0]
            type(self).attempts[recipient] += 1
            if recipient in type(self).refuse or recipient in type(self).refuse_once:
                type(self).refuse_once.discard(recipient)
                raise smtplib.SMTPRecipientsRefused(
                    {recipient: (550, b"recipient rejected before acceptance")}
                )
            type(self).accepted.append(message)
            sent += 1
        return sent


class UnknownOutcomeBackend(BaseEmailBackend):
    """A local mail transport that simulates a submission timeout."""

    attempts = 0

    def send_messages(self, email_messages):
        type(self).attempts += len(email_messages)
        raise TimeoutError("simulated transport timeout")


class SlowSuccessBackend(BaseEmailBackend):
    """A local transport used to make concurrent send attempts overlap."""

    accepted: list = []
    lock = threading.Lock()

    def send_messages(self, email_messages):
        time_module.sleep(0.15)
        with type(self).lock:
            type(self).accepted.extend(email_messages)
        return len(email_messages)


@pytest.fixture(autouse=True)
def safe_mail_transport():
    """Keep every test mail in process memory; no test connects to real SMTP."""
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.test.invalid",
        EMAIL_PORT=587,
        EMAIL_HOST_USER="platform-test-sender",
        EMAIL_HOST_PASSWORD="MAIL002_TEST_ONLY_SECRET",
        EMAIL_USE_TLS=True,
        DEFAULT_FROM_EMAIL="noreply@example.test",
    ):
        if hasattr(mail, "outbox"):
            mail.outbox.clear()
        ExplicitRefusalBackend.attempts.clear()
        ExplicitRefusalBackend.accepted.clear()
        ExplicitRefusalBackend.refuse.clear()
        ExplicitRefusalBackend.refuse_once.clear()
        UnknownOutcomeBackend.attempts = 0
        SlowSuccessBackend.accepted.clear()
        yield
        if hasattr(mail, "outbox"):
            mail.outbox.clear()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def frozen_framework_clock(monkeypatch):
    """Control the public Django clock used by application requests and commands."""
    original_now = timezone.now
    clock = {"now": original_now()}

    def read_now():
        return clock["now"]

    def travel(local_day: date, hour: int, minute: int = 0):
        local_value = datetime.combine(local_day, time(hour, minute), tzinfo=BEIJING)
        clock["now"] = local_value.astimezone(dt_timezone.utc)

    monkeypatch.setattr(timezone, "now", read_now)
    return travel


@pytest.mark.django_db(transaction=True)
def test_due_command_sends_complete_ordered_beijing_day_including_cross_midnight(client, frozen_framework_clock):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    owner, verification_token = _verified_user(
        client, "daily-owner", "09:00", address="daily-owner@example.test"
    )
    other, _ = _verified_user(
        client, "daily-other", "09:00", address="daily-other@example.test"
    )

    _create_application(
        client,
        owner,
        company_name="跨入当天的晨间面试",
        position_name="后端工程师",
        stage_time=_iso_at(today - timedelta(days=1), 23, 30),
        stage_duration=120,
        stage="first_interview",
    )
    _create_application(
        client,
        owner,
        company_name="午夜前结束的安排",
        stage_time=_iso_at(today - timedelta(days=1), 22, 0),
        stage_duration=120,
        stage="written_test",
    )
    _create_application(
        client,
        owner,
        company_name="次日午夜开始的安排",
        stage_time=_iso_at(today + timedelta(days=1), 0, 0),
        stage_duration=60,
        stage="hr_interview",
    )
    _create_application(
        client,
        owner,
        company_name="当天上午后续安排",
        position_name="数据分析师",
        stage_time=_iso_at(today, 10, 0),
        stage_duration=45,
        stage="second_interview",
    )
    _create_application(
        client,
        other,
        company_name="OTHER_USER_PRIVATE_SCHEDULE",
        stage_time=_iso_at(today, 10, 0),
        stage_duration=45,
        stage="written_test",
    )

    frozen_framework_clock(today, 9, 7)  # The scheduler was delayed within the same Beijing date.
    output = _run_command()

    sent = _captured_messages()
    assert len(sent) == 2
    summaries = {message.to[0]: message for message in sent}
    owner_summary = summaries["daily-owner@example.test"]
    other_summary = summaries["daily-other@example.test"]
    assert today.isoformat() in owner_summary.body
    assert "Asia/Shanghai" in owner_summary.body or "北京时间" in owner_summary.body
    assert "跨入当天的晨间面试" in owner_summary.body
    assert "后端工程师" in owner_summary.body
    assert "23:30" in owner_summary.body
    assert "01:30" in owner_summary.body
    assert "first_interview" in owner_summary.body or "一面" in owner_summary.body
    assert "当天上午后续安排" in owner_summary.body
    assert "数据分析师" in owner_summary.body
    assert owner_summary.body.index("跨入当天的晨间面试") < owner_summary.body.index("当天上午后续安排")
    assert "午夜前结束的安排" not in owner_summary.body
    assert "次日午夜开始的安排" not in owner_summary.body
    assert "OTHER_USER_PRIVATE_SCHEDULE" not in owner_summary.body
    assert "跨入当天的晨间面试" not in other_summary.body
    assert "OTHER_USER_PRIVATE_SCHEDULE" in other_summary.body
    assert _delivery(client, owner)["status"] == "accepted"
    assert _delivery(client, other)["status"] == "accepted"
    assert output.strip()
    assert "MAIL002_TEST_ONLY_SECRET" not in output
    assert verification_token not in output


@pytest.mark.django_db(transaction=True)
def test_zero_arrangements_still_send_the_explicit_empty_day_message(client, frozen_framework_clock):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    owner, _ = _verified_user(client, "empty-day", "09:00")

    frozen_framework_clock(today, 9, 0)
    _run_command()

    sent = _captured_messages()
    assert len(sent) == 1
    assert today.isoformat() in sent[0].body
    assert "今日无安排" in sent[0].body
    assert _delivery(client, owner)["status"] == "accepted"


@pytest.mark.django_db(transaction=True)
def test_enabling_after_configured_time_does_not_send_until_the_next_beijing_day(
    client, frozen_framework_clock
):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 10, 0)
    owner, _ = _verified_user(client, "late-enable", "09:00")

    frozen_framework_clock(today, 10, 1)
    _run_command()
    assert _captured_messages() == []
    assert _delivery(client, owner) is None

    next_day = today + timedelta(days=1)
    frozen_framework_clock(next_day, 9, 5)
    _run_command()
    sent = _captured_messages()
    assert len(sent) == 1
    assert next_day.isoformat() in sent[0].body
    assert today.isoformat() not in sent[0].body
    assert _delivery(client, owner)["date"] == next_day.isoformat()
    assert _delivery(client, owner)["status"] == "accepted"


@pytest.mark.django_db(transaction=True)
def test_disabled_unverified_and_not_yet_due_users_are_skipped(client, frozen_framework_clock):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    disabled, _ = _verified_user(client, "disabled-user", "09:00", enabled=False)
    pending = _register_and_login(client, "unverified-user")
    pending_settings = client.patch(
        SETTINGS_URL,
        {"recipient_email": "unverified@example.test", "daily_time": "09:00"},
        content_type="application/json",
        **_headers(pending),
    )
    assert pending_settings.status_code == 200
    not_due, _ = _verified_user(client, "not-due-user", "11:00")

    frozen_framework_clock(today, 9, 5)
    _run_command()

    assert _captured_messages() == []
    assert _delivery(client, disabled) is None
    assert _delivery(client, pending) is None
    assert _delivery(client, not_due) is None


@pytest.mark.django_db(transaction=True)
def test_repeat_and_concurrent_commands_claim_one_user_day_at_most_once(
    client, frozen_framework_clock
):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    owner, _ = _verified_user(client, "concurrent-user", "09:00")
    frozen_framework_clock(today, 9, 0)

    with override_settings(EMAIL_BACKEND="backend.tests.test_mail_002.SlowSuccessBackend"):
        start = threading.Barrier(3)

        def run_concurrently():
            from django.db import close_old_connections

            close_old_connections()
            try:
                start.wait(timeout=5)
                _run_command()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(run_concurrently)
            second = pool.submit(run_concurrently)
            start.wait(timeout=5)
            first.result(timeout=20)
            second.result(timeout=20)

        _run_command()

    assert len(SlowSuccessBackend.accepted) == 1
    assert _delivery(client, owner)["date"] == today.isoformat()
    assert _delivery(client, owner)["status"] == "accepted"


@pytest.mark.django_db(transaction=True)
def test_explicit_smtp_refusal_is_retryable_and_one_users_failure_does_not_block_others(
    client, frozen_framework_clock
):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    rejected, _ = _verified_user(client, "reject-user", "09:00", address="reject@example.test")
    healthy, _ = _verified_user(client, "healthy-user", "09:00", address="healthy@example.test")
    ExplicitRefusalBackend.refuse_once.add("reject@example.test")
    frozen_framework_clock(today, 9, 0)

    with override_settings(EMAIL_BACKEND="backend.tests.test_mail_002.ExplicitRefusalBackend"):
        _run_command()
        first_rejected_state = _delivery(client, rejected)
        assert first_rejected_state["status"] == "failed_retryable"
        assert _delivery(client, healthy)["status"] == "accepted"

        frozen_framework_clock(today, 9, 4)
        _run_command()
        assert ExplicitRefusalBackend.attempts["reject@example.test"] == 1

        frozen_framework_clock(today, 9, 5)
        _run_command()
        assert _delivery(client, rejected)["status"] == "accepted"
        assert _delivery(client, healthy)["status"] == "accepted"

        frozen_framework_clock(today, 9, 10)
        _run_command()

    assert ExplicitRefusalBackend.attempts["reject@example.test"] == 2
    assert ExplicitRefusalBackend.attempts["healthy@example.test"] == 1
    assert {message.to[0] for message in ExplicitRefusalBackend.accepted} == {
        "reject@example.test",
        "healthy@example.test",
    }


@pytest.mark.django_db(transaction=True)
def test_explicit_refusal_stops_after_three_retries_and_becomes_terminal_failure(
    client, frozen_framework_clock
):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    rejected, _ = _verified_user(client, "refused-forever", "09:00", address="always-refuse@example.test")
    ExplicitRefusalBackend.refuse.add("always-refuse@example.test")

    with override_settings(EMAIL_BACKEND="backend.tests.test_mail_002.ExplicitRefusalBackend"):
        for hour, minute in ((9, 0), (9, 5), (9, 10), (9, 15)):
            frozen_framework_clock(today, hour, minute)
            _run_command()

        assert ExplicitRefusalBackend.attempts["always-refuse@example.test"] == 4
        assert _delivery(client, rejected)["status"] == "failed"

        frozen_framework_clock(today, 9, 20)
        _run_command()

    assert ExplicitRefusalBackend.attempts["always-refuse@example.test"] == 4


@pytest.mark.django_db(transaction=True)
def test_retry_rebuilds_the_summary_from_current_application_data(client, frozen_framework_clock):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    owner, _ = _verified_user(client, "retry-refetch", "09:00", address="retry-refetch@example.test")
    application = _create_application(
        client,
        owner,
        company_name="DELETED_BEFORE_RETRY",
        stage_time=_iso_at(today, 10, 0),
        stage_duration=30,
        stage="second_interview",
    )
    ExplicitRefusalBackend.refuse_once.add("retry-refetch@example.test")

    with override_settings(EMAIL_BACKEND="backend.tests.test_mail_002.ExplicitRefusalBackend"):
        frozen_framework_clock(today, 9, 0)
        _run_command()
        assert _delivery(client, owner)["status"] == "failed_retryable"

        deleted = client.delete(
            f"{APPLICATIONS_URL}{application['id']}/",
            **_headers(owner),
        )
        assert deleted.status_code == 204
        frozen_framework_clock(today, 9, 5)
        _run_command()

    sent = [message for message in ExplicitRefusalBackend.accepted if message.to == ["retry-refetch@example.test"]]
    assert len(sent) == 1
    assert "DELETED_BEFORE_RETRY" not in sent[0].body
    assert "今日无安排" in sent[0].body
    assert _delivery(client, owner)["status"] == "accepted"


@pytest.mark.django_db(transaction=True)
def test_uncertain_timeout_is_recorded_unknown_and_never_automatically_retried(
    client, frozen_framework_clock
):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    owner, _ = _verified_user(client, "unknown-user", "09:00")
    frozen_framework_clock(today, 9, 0)

    with override_settings(EMAIL_BACKEND="backend.tests.test_mail_002.UnknownOutcomeBackend"):
        _run_command()
        assert _delivery(client, owner)["status"] == "unknown"
        _run_command()

    assert UnknownOutcomeBackend.attempts == 1
    assert _delivery(client, owner)["status"] == "unknown"


@pytest.mark.django_db(transaction=True)
def test_missing_smtp_configuration_is_observable_without_false_acceptance(
    client, frozen_framework_clock, caplog
):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    owner, _ = _verified_user(client, "no-smtp-user", "09:00")
    frozen_framework_clock(today, 9, 0)

    with override_settings(
        EMAIL_HOST="",
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",
    ):
        output = _run_command()

    delivery = _delivery(client, owner)
    assert delivery is None or delivery["status"] != "accepted"
    diagnostic = (output + caplog.text).lower()
    assert "smtp" in diagnostic or "email" in diagnostic or "mail" in diagnostic
    assert "MAIL002_TEST_ONLY_SECRET" not in output + caplog.text
    assert all("@" not in str(value) for value in [output])


@pytest.mark.django_db(transaction=True)
def test_delivery_diagnostics_and_public_settings_do_not_expose_secrets_or_message_body(
    client, frozen_framework_clock, caplog
):
    today = timezone.localtime().date()
    frozen_framework_clock(today, 8, 0)
    owner, verification_token = _verified_user(client, "redaction-user", "09:00")
    _create_application(
        client,
        owner,
        company_name="PRIVATE_SCHEDULE_BODY_SENTINEL",
        stage_time=_iso_at(today, 10, 0),
        stage_duration=30,
        stage="ai_interview",
    )
    frozen_framework_clock(today, 9, 0)

    output = _run_command()
    public_settings = _json(client.get(SETTINGS_URL, **_headers(owner)))
    observed = output + caplog.text + str(public_settings)

    assert "MAIL002_TEST_ONLY_SECRET" not in observed
    assert verification_token not in observed
    assert "PRIVATE_SCHEDULE_BODY_SENTINEL" not in output + caplog.text
    assert "redaction-user@example.test" not in output + caplog.text
    assert not any(
        key in public_settings
        for key in ("token", "verification_token", "smtp_password", "smtp_host_password")
    )
    assert public_settings["last_delivery"]["status"] == "accepted"


def _run_command() -> str:
    from io import StringIO

    output = StringIO()
    call_command("send_daily_summaries", stdout=output, stderr=output)
    return output.getvalue()


def _register_and_login(client, prefix: str):
    username = f"{prefix}-{uuid.uuid4().hex[:10]}"
    credentials = {
        "username": username,
        "email": f"{username}@example.test",
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
    return {"access": logged_in.json()["access"], "username": username}


def _verified_user(client, prefix: str, daily_time: str, *, enabled=True, address=None):
    from django.core import mail as django_mail

    session = _register_and_login(client, prefix)
    recipient = address or f"{session['username']}@example.test"
    configured = client.patch(
        SETTINGS_URL,
        {"recipient_email": recipient, "daily_time": daily_time, "enabled": False},
        content_type="application/json",
        **_headers(session),
    )
    assert configured.status_code == 200
    requested = client.post(
        REQUEST_VERIFICATION_URL,
        {},
        content_type="application/json",
        **_headers(session),
    )
    assert requested.status_code == 202
    assert django_mail.outbox
    verification_body = django_mail.outbox[-1].body
    match = re.search(r"[?&]token=([^&\s\"'<>]+)", verification_body)
    assert match, "verification test message did not contain the public link token"
    token = unquote(match.group(1))
    verified = client.post(
        VERIFY_URL,
        {"token": token},
        content_type="application/json",
        **_headers(session),
    )
    assert verified.status_code == 200
    changed = client.patch(
        SETTINGS_URL,
        {"enabled": enabled},
        content_type="application/json",
        **_headers(session),
    )
    assert changed.status_code == 200
    # Keep only daily summary messages in the observable test-mail capture.
    django_mail.outbox.clear()
    return session, token


def _headers(session):
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _delivery(client, session):
    response = client.get(SETTINGS_URL, **_headers(session))
    assert response.status_code == 200
    return _json(response)["last_delivery"]


def _iso_at(day: date, hour: int, minute: int):
    return f"{day.isoformat()}T{hour:02d}:{minute:02d}:00+08:00"


def _create_application(
    client,
    session,
    *,
    company_name,
    position_name="候选岗位",
    stage_time,
    stage_duration,
    stage,
):
    stage_fields = {
        "ai_interview": ("ai_interview_time", "ai_interview_duration_minutes"),
        "written_test": ("written_test_time", "written_test_duration_minutes"),
        "first_interview": ("first_interview_time", "first_interview_duration_minutes"),
        "second_interview": ("second_interview_time", "second_interview_duration_minutes"),
        "third_interview": ("third_interview_time", "third_interview_duration_minutes"),
        "hr_interview": ("hr_interview_time", "hr_interview_duration_minutes"),
    }
    payload = {
        "company_name": company_name,
        "position_name": position_name,
        # APP-010 canonical status; MAIL-002 assertions concern delivery behavior.
        "application_status": "assessment",
        "application_time": _iso_at(timezone.localtime().date(), 7, 0),
        "ai_interview_time": None,
        "written_test_time": None,
        "first_interview_time": None,
        "second_interview_time": None,
        "third_interview_time": None,
        "hr_interview_time": None,
        "notes": "MAIL-002 black-box fixture",
    }
    time_field, duration_field = stage_fields[stage]
    payload[time_field] = stage_time
    payload[duration_field] = stage_duration
    response = client.post(
        APPLICATIONS_URL,
        payload,
        content_type="application/json",
        **_headers(session),
    )
    assert response.status_code == 201, response.content
    return _json(response)


def _captured_messages():
    return list(mail.outbox)
