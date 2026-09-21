"""Black-box checks for the DB-001 Django/PostgreSQL baseline."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
from django.test import Client


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"


def _run_manage(*args: str) -> subprocess.CompletedProcess[str]:
    if shutil.which("uv") is None:
        pytest.skip("uv 不可用，不能将工具缺失误判为 DB-001 契约失败")
    return subprocess.run(
        ["uv", "run", "--no-sync", "python", "manage.py", *args],
        cwd=BACKEND_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _database_probe() -> subprocess.CompletedProcess[str]:
    probe = (
        "from django.db import connection; "
        "connection.ensure_connection(); "
        "print('connection=ok'); "
        "print('vendor=' + connection.vendor); "
        "print('engine=' + connection.settings_dict.get('ENGINE', '')); "
        "print('dev_name=' + str(connection.settings_dict.get('NAME', ''))); "
        "test_name = connection.settings_dict.get('TEST', {}).get('NAME') or connection.creation._get_test_db_name(); "
        "print('test_name=' + str(test_name))"
    )
    return _run_manage("shell", "-c", probe)


def test_backend_dependency_lock_contains_db_stack() -> None:
    project = tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((BACKEND_ROOT / "uv.lock").read_text(encoding="utf-8"))

    declared = {
        str(item).split("[", 1)[0].lower()
        for item in project["project"].get("dependencies", [])
    }
    locked = {
        str(package["name"]).lower()
        for package in lock.get("package", [])
        if "name" in package
    }

    for package_name in (
        "django",
        "djangorestframework",
        "djangorestframework-simplejwt",
    ):
        assert package_name in declared, f"pyproject.toml 缺少锁定的 {package_name} 依赖"
        assert package_name in locked, f"uv.lock 缺少 {package_name} 包记录"

    postgres_drivers = {"psycopg", "psycopg2-binary"}
    assert declared & postgres_drivers, "pyproject.toml 缺少 PostgreSQL 驱动依赖"
    assert locked & postgres_drivers, "uv.lock 缺少 PostgreSQL 驱动包记录"


def test_database_connection_is_postgresql_and_test_database_isolated() -> None:
    result = _database_probe()

    assert result.returncode == 0, (
        "公开 Django 数据库探针命令失败，无法确认 PostgreSQL 可用:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    output = result.stdout
    assert "connection=ok" in output
    assert "vendor=postgresql" in output, (
        "Django 必须使用 DATABASE_URL 指向 PostgreSQL，不能静默回退到 SQLite"
    )
    assert "engine=django.db.backends.postgresql" in output

    values = dict(
        line.split("=", 1)
        for line in output.splitlines()
        if "=" in line and line.split("=", 1)[0] in {"dev_name", "test_name"}
    )
    assert values.get("dev_name")
    assert values.get("test_name")
    assert values["test_name"] != values["dev_name"], (
        "Django 测试数据库必须与开发数据库使用不同连接目标"
    )


def test_public_manage_check_and_migration_drift_commands_succeed() -> None:
    for args in (
        ("check",),
        ("makemigrations", "--check", "--dry-run"),
        ("migrate", "--plan"),
    ):
        result = _run_manage(*args)
        assert result.returncode == 0, (
            f"公开命令 {' '.join(args)} 失败:\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )


def test_public_test_runner_can_prepare_the_isolated_database() -> None:
    probe = _database_probe()
    assert probe.returncode == 0 and "vendor=postgresql" in probe.stdout, (
        "未确认 PostgreSQL 和独立测试数据库前，不执行会创建测试库的公开测试命令"
    )

    result = _run_manage("test", "--noinput", "--verbosity", "0")
    assert result.returncode == 0, (
        "公开 Django 测试命令无法准备独立测试数据库:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


def test_public_health_api_returns_json_baseline() -> None:
    response = Client().get("/api/v1/health/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert json.loads(response.content) == {"status": "ok"}
