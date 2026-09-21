"""Black-box release-gate checks for REL-001.

These checks exercise only the public command surface and the public HTTP
contract.  They intentionally do not import application implementation
modules.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from django.test import Client


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_locked_backend_quality_tools_are_available_after_uv_sync():
    """Ruff and coverage must be runnable from the frozen test environment."""

    failures: list[str] = []
    for tool in ("ruff", "coverage"):
        result = _run("uv", "run", "--no-sync", tool, "--version", cwd=BACKEND)
        if result.returncode != 0:
            failures.append(
                f"{tool}: exit={result.returncode}; "
                f"stdout={result.stdout.strip()!r}; stderr={result.stderr.strip()!r}"
            )
    assert not failures, "REL-001 locked quality tools are unavailable: " + " | ".join(failures)


def test_frontend_public_scripts_expose_coverage_and_build_gates():
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    scripts = package.get("scripts", {})
    assert "lint" in scripts
    assert "build" in scripts
    assert "test" in scripts

    vitest_config = (FRONTEND / "vitest.config.mts").read_text(encoding="utf-8")
    assert "coverage" in vitest_config, (
        "REL-001 requires a frontend coverage gate, but the public Vitest "
        "configuration exposes no coverage configuration"
    )


@pytest.mark.django_db
def test_public_release_smoke_health_and_anonymous_auth_boundary():
    client = Client()

    health = client.get("/api/v1/health/")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    register = client.post(
        "/api/v1/auth/register/",
        {
            "username": "rel001_smoke_user",
            "email": "rel001_smoke@example.com",
            "password": "StrongPass_123",
            "password_confirm": "StrongPass_123",
        },
        content_type="application/json",
    )
    assert register.status_code in {201, 409}
    if register.status_code == 201:
        assert "password" not in register.json()

    applications = client.get("/api/v1/applications/")
    assert applications.status_code == 401
