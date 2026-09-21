"""Black-box security checks for SEC-001.

These tests observe only public management checks, HTTP responses, and emitted
request logs. They do not inspect Django settings or production source code.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from django.test import Client


BACKEND_ROOT = Path(__file__).resolve().parents[1]
HEALTH_URL = "/api/v1/health/"
REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
ME_URL = "/api/v1/auth/me/"
PASSWORD = "StrongPass_123"


def _manage_check(env_updates: dict[str, str] | None = None, remove: tuple[str, ...] = ()):
    """Run the public deployment check in a separate process with controlled env."""
    if shutil.which("uv") is None:
        pytest.fail("uv is required by the project environment contract")

    environment = os.environ.copy()
    for name in remove:
        environment.pop(name, None)
    environment.update(env_updates or {})
    return subprocess.run(
        ["uv", "run", "--no-sync", "python", "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _combined_process_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout}\n{result.stderr}"


def _assert_safe_error(response, *secrets: str) -> None:
    body = response.content.decode(errors="replace")
    lowered = body.lower()
    assert "traceback" not in lowered
    assert "stack trace" not in lowered
    assert "syntax error at or near" not in lowered
    assert "select * from" not in lowered
    assert "authorization" not in lowered
    for secret in secrets:
        assert secret not in body


def test_missing_sensitive_configuration_is_rejected_by_public_deploy_check():
    result = _manage_check(
        {
            "DJANGO_SECRET_KEY": "",
            "DATABASE_URL": os.environ.get(
                "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/postgres"
            ),
            "DJANGO_DEBUG": "false",
            "CORS_ALLOWED_ORIGINS": "",
        },
        remove=("SECRET_KEY",),
    )

    output = _combined_process_output(result).lower()
    assert result.returncode != 0, "missing secret configuration must not fall back to a runnable unsafe default"
    assert any(marker in output for marker in ("secret", "secret_key", "required"))


def test_production_debug_and_wildcard_cors_are_rejected_by_public_deploy_check():
    result = _manage_check(
        {
            "DJANGO_SECRET_KEY": "insecure-test-only-key",
            "DATABASE_URL": os.environ.get(
                "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/postgres"
            ),
            "DJANGO_DEBUG": "true",
            "CORS_ALLOWED_ORIGINS": "*",
        }
    )

    output = _combined_process_output(result).lower()
    assert result.returncode != 0, "production debug/wildcard CORS must not pass the deployment safety check"
    assert "debug" in output or "cors" in output or "origin" in output


@pytest.mark.django_db
def test_public_response_has_content_type_and_referrer_security_headers_and_no_wildcard_cors():
    response = Client().get(HEALTH_URL, HTTP_ORIGIN="https://evil.example")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options", "").lower() == "nosniff"
    assert response.headers.get("Referrer-Policy")
    assert response.headers.get("Access-Control-Allow-Origin") != "*"


@pytest.mark.django_db
def test_error_responses_do_not_echo_password_token_authorization_sql_or_stack_details():
    client = Client()
    password = "NeverEchoThisPassword_123"
    token = "Bearer never-echo-this-token"
    response = client.post(
        REGISTER_URL,
        {"username": "x", "email": "not-an-email", "password": password, "password_confirm": password},
        HTTP_AUTHORIZATION=token,
        content_type="application/json",
    )

    assert 400 <= response.status_code < 500
    _assert_safe_error(response, password, token)

    protected = client.get(ME_URL, HTTP_AUTHORIZATION=token)
    assert protected.status_code == 401
    _assert_safe_error(protected, password, token)


@pytest.mark.django_db
def test_request_logs_are_observable_and_redact_authorization_and_credentials(caplog):
    client = Client()
    password = "LogSecretPassword_123"
    token = "Bearer log-secret-token"

    with caplog.at_level("INFO"):
        response = client.post(
            LOGIN_URL,
            {"username": "missing-user", "password": password},
            HTTP_AUTHORIZATION=token,
            content_type="application/json",
        )

    assert 400 <= response.status_code < 500
    messages = [record.getMessage() for record in caplog.records]
    assert messages, "a public authentication request should produce an observable request log"
    joined = "\n".join(messages)
    assert LOGIN_URL in joined or "login" in joined.lower()
    assert password not in joined
    assert token not in joined
    assert "authorization:" not in joined.lower()


@pytest.mark.django_db
def test_login_rate_limit_entry_is_safe_if_exposed_and_does_not_return_server_errors():
    client = Client()
    responses = [
        client.post(
            LOGIN_URL,
            {"username": "rate-limit-probe", "password": "wrong-password"},
            content_type="application/json",
            REMOTE_ADDR="198.51.100.27",
        )
        for _ in range(8)
    ]

    assert all(response.status_code in {400, 401, 429} for response in responses)
    for response in responses:
        _assert_safe_error(response, "wrong-password")

    rate_limited = [response for response in responses if response.status_code == 429]
    if rate_limited:
        assert all(response.status_code == 429 for response in responses[-2:])
