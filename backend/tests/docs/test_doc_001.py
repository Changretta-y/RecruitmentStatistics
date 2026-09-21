"""Black-box OpenAPI and public documentation checks for DOC-001."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest
from django.test import Client


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
SCHEMA_ENDPOINTS = (
    "/api/schema/",
    "/api/v1/schema/",
    "/api/schema.json",
    "/api/v1/schema.json",
)


def _test_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.setdefault("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/postgres")
    environment.setdefault(
        "DJANGO_SECRET_KEY",
        "doc001-test-only-key-0123456789-abcdefghijklmnopqrstuvwxyz",
    )
    environment.setdefault("SECRET_KEY", environment["DJANGO_SECRET_KEY"])
    return environment


def _generate_schema() -> dict:
    with tempfile.TemporaryDirectory(prefix="doc001-schema-") as temporary_directory:
        schema_path = Path(temporary_directory) / "openapi.json"
        result = subprocess.run(
            [
                "uv",
                "run",
                "--no-sync",
                "python",
                "manage.py",
                "spectacular",
                "--file",
                str(schema_path),
            ],
            cwd=BACKEND_ROOT,
            env=_test_environment(),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, (
            "公开 schema 生成命令失败："
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}"
        )
        assert schema_path.exists(), "schema 生成命令未产生公开 schema 文件"
        return json.loads(schema_path.read_text(encoding="utf-8"))


def _schema_from_public_entry_or_command() -> dict:
    client = Client()
    for endpoint in SCHEMA_ENDPOINTS:
        response = client.get(endpoint, HTTP_ACCEPT="application/json")
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                pytest.fail(f"公开 schema endpoint {endpoint} 返回的不是 JSON schema")
    return _generate_schema()


def _operation(schema: dict, path: str, method: str) -> dict:
    path_item = schema.get("paths", {}).get(path)
    assert path_item is not None, f"schema 缺少公开路径 {path}"
    operation = path_item.get(method.lower())
    assert operation is not None, f"schema 缺少 {method.upper()} {path}"
    return operation


def test_schema_entry_or_generation_covers_auth_application_and_bearer_contract():
    schema = _schema_from_public_entry_or_command()
    paths = schema.get("paths", {})

    _operation(schema, "/api/v1/auth/register/", "post")
    _operation(schema, "/api/v1/auth/login/", "post")
    _operation(schema, "/api/v1/auth/refresh/", "post")
    _operation(schema, "/api/v1/auth/logout/", "post")
    _operation(schema, "/api/v1/auth/me/", "get")
    _operation(schema, "/api/v1/applications/", "get")
    _operation(schema, "/api/v1/applications/", "post")
    detail_path = next(
        (path for path in paths if path.rstrip("/") in {"/api/v1/applications/{id}", "/api/v1/applications/{pk}"}),
        None,
    )
    assert detail_path is not None, "schema 缺少投递详情路径"
    for method in ("get", "patch", "delete"):
        assert method in paths[detail_path], f"schema 缺少 {method.upper()} {detail_path}"

    schemes = schema.get("components", {}).get("securitySchemes", {})
    assert any(
        scheme.get("type") == "http" and scheme.get("scheme", "").lower() == "bearer"
        for scheme in schemes.values()
        if isinstance(scheme, dict)
    ), "schema 缺少 Bearer HTTP security scheme"


def test_schema_describes_query_pagination_and_error_contract():
    schema = _schema_from_public_entry_or_command()
    list_operation = _operation(schema, "/api/v1/applications/", "get")
    parameter_names = {
        parameter.get("name")
        for parameter in list_operation.get("parameters", [])
        if isinstance(parameter, dict)
    }
    assert {"page", "page_size", "search", "ordering"}.issubset(parameter_names)
    assert {"application_status", "stage", "application_time_after", "application_time_before"}.issubset(
        parameter_names
    )

    serialized = json.dumps(schema, ensure_ascii=False)
    assert '"code"' in serialized
    assert '"details"' in serialized
    for expected_status in ("400", "401", "404"):
        assert expected_status in serialized, f"schema 未描述错误状态 {expected_status}"


def _public_documentation() -> str:
    candidates = [REPOSITORY_ROOT / "README.md"]
    docs_root = REPOSITORY_ROOT / "docs"
    candidates.extend(path for path in docs_root.glob("*.md") if path.is_file())
    candidates.extend(path for path in docs_root.glob("*/*.md") if path.is_file() and path.parent.name not in {
        "agents",
        "tasks",
        "test-reports",
        "implementation-notes",
        "acceptance",
    })
    existing = [path for path in candidates if path.exists()]
    assert existing, "缺少公开开发/部署文档入口"
    return "\n".join(path.read_text(encoding="utf-8") for path in existing)


def test_public_docs_explain_startup_migration_backend_frontend_and_e2e_commands():
    documentation = _public_documentation()
    required_markers = {
        "uv sync --frozen": "后端依赖同步",
        "uv run": "后端命令入口",
        "migrate": "数据库迁移",
        "nvm use": "Node 运行时切换",
        "npm ci": "前端依赖同步",
        "npm run test": "前端测试",
        "e2e": "E2E 测试",
    }
    missing = [label for marker, label in required_markers.items() if marker.lower() not in documentation.lower()]
    assert not missing, f"公开文档缺少命令说明：{', '.join(missing)}"


def test_public_docs_do_not_contain_real_credentials_or_production_addresses():
    documentation = _public_documentation()
    forbidden = [
        re.compile(r"postgresql://[^\s`'\"]+:[^\s`'\"]+@[^\s`'\"]+"),
        re.compile(r"(?:password|passwd|secret|token)\s*[:=]\s*['\"]?[^\s'\"]{8,}", re.I),
        re.compile(r"https?://(?:api\.|prod|production)[^\s`'\"]+", re.I),
    ]
    for pattern in forbidden:
        assert not pattern.search(documentation), f"公开文档疑似包含凭据或生产地址：{pattern.pattern}"
