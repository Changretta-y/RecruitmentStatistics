"""Black-box checks for the BASE-ENV-001 repository environment contract."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"


def _required_file(relative_path: str) -> Path:
    path = REPOSITORY_ROOT / relative_path
    assert path.is_file(), f"公开环境契约文件缺失: {relative_path}"
    return path


def _read_text(relative_path: str) -> str:
    return _required_file(relative_path).read_text(encoding="utf-8").strip()


def _run_tool(tool: str, args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    command = tool
    if tool == "npm" and os.name == "nt":
        command = next(
            (candidate for candidate in ("npm.cmd", "npm.exe") if shutil.which(candidate)),
            tool,
        )
    if shutil.which(command) is None:
        pytest.skip(f"测试工具不可用，不能将其误判为契约失败: {tool}")
    return subprocess.run(
        [command, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _python_version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)(?:\.(\d+))?", value.strip())
    assert match, f".python-version 必须是可解析的 Python 版本: {value!r}"
    return tuple(int(part or 0) for part in match.groups())


def test_python_version_file_satisfies_pyproject_requires_python() -> None:
    selected = _python_version_tuple(_read_text(".python-version"))
    project = tomllib.loads(_read_text("backend/pyproject.toml"))
    requires_python = project["project"]["requires-python"]

    lower_bound = re.search(r">=\s*(\d+)\.(\d+)(?:\.(\d+))?", requires_python)
    assert lower_bound, f"无法解析 requires-python 公开约束: {requires_python!r}"
    minimum = tuple(int(part or 0) for part in lower_bound.groups())
    assert selected >= minimum, (
        f".python-version={selected} 不满足 pyproject.toml 的 {requires_python!r}"
    )

    upper_bound = re.search(r"<\s*(\d+)\.(\d+)(?:\.(\d+))?", requires_python)
    if upper_bound:
        maximum = tuple(int(part or 0) for part in upper_bound.groups())
        assert selected < maximum, (
            f".python-version={selected} 不满足 pyproject.toml 的 {requires_python!r}"
        )


def test_uv_lock_matches_project_python_constraint() -> None:
    project = tomllib.loads(_read_text("backend/pyproject.toml"))
    lock = tomllib.loads(_read_text("backend/uv.lock"))

    assert lock.get("requires-python") == project["project"]["requires-python"], (
        "backend/uv.lock 的 requires-python 必须与 backend/pyproject.toml 一致"
    )


def test_node_version_file_and_package_engine_are_consistent() -> None:
    selected = _read_text(".nvmrc")
    package = json.loads(_read_text("frontend/package.json"))
    engine = package.get("engines", {}).get("node")
    assert isinstance(engine, str) and engine.strip(), (
        "frontend/package.json 必须声明 engines.node"
    )

    version_match = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", selected)
    assert version_match, f".nvmrc 必须是可解析的 Node.js 版本: {selected!r}"
    major, minor, patch = version_match.groups()
    assert re.search(rf"(?<!\d){major}(?:\.{minor})?(?:\.{patch})?(?!\d)", engine), (
        f".nvmrc={selected!r} 与 engines.node={engine!r} 未表达同一版本约束"
    )


def test_frontend_lockfile_and_required_npm_scripts_are_present() -> None:
    package = json.loads(_read_text("frontend/package.json"))
    lock = json.loads(_read_text("frontend/package-lock.json"))

    assert lock.get("lockfileVersion", 0) >= 2, "package-lock.json 必须是 npm ci 支持的锁文件"
    root_package = lock.get("packages", {}).get("")
    assert isinstance(root_package, dict), "package-lock.json 缺少根 package 元数据"
    assert root_package.get("name") == package.get("name"), (
        "package-lock.json 根 package name 必须与 package.json 一致"
    )
    assert root_package.get("version") == package.get("version"), (
        "package-lock.json 根 package version 必须与 package.json 一致"
    )

    scripts = package.get("scripts", {})
    for script_name in ("test", "lint", "build"):
        assert isinstance(scripts.get(script_name), str) and scripts[script_name].strip(), (
            f"frontend/package.json 缺少可启动的 npm run {script_name} 脚本"
        )


def test_npm_ci_accepts_frontend_lockfile_without_rewriting_it() -> None:
    _required_file("frontend/package.json")
    _required_file("frontend/package-lock.json")
    result = _run_tool(
        "npm",
        ["ci", "--ignore-scripts", "--no-audit", "--no-fund", "--dry-run"],
        cwd=FRONTEND_ROOT,
    )
    assert result.returncode == 0, (
        "npm ci 无法依据 package-lock.json 完成冻结安装校验:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


def test_gitignore_excludes_local_environment_state_and_required_files_are_tracked() -> None:
    ignore_text = _read_text(".gitignore")
    normalized = {line.strip().replace("\\", "/") for line in ignore_text.splitlines()}

    assert any(".venv" in line for line in normalized), ".gitignore 必须忽略 .venv"
    assert any("node_modules" in line for line in normalized), (
        ".gitignore 必须忽略 node_modules"
    )
    assert any(line in normalized or ".env" in line for line in normalized), (
        ".gitignore 必须忽略本地密钥/环境文件"
    )

    for relative_path in (
        ".python-version",
        ".nvmrc",
        "backend/uv.lock",
        "frontend/package-lock.json",
    ):
        _required_file(relative_path)
        result = _run_tool(
            "git",
            [
                "-c",
                "safe.directory=G:/bk-incident/job",
                "ls-files",
                "--error-unmatch",
                relative_path,
            ],
            cwd=REPOSITORY_ROOT,
        )
        assert result.returncode == 0, f"版本/锁文件未被 Git 跟踪: {relative_path}"


def test_ci_uses_declared_versions_and_frozen_install_commands() -> None:
    workflow_root = REPOSITORY_ROOT / ".github" / "workflows"
    workflow_files = (
        list(workflow_root.glob("*.yml")) + list(workflow_root.glob("*.yaml"))
        if workflow_root.is_dir()
        else []
    )
    assert workflow_files, "必须存在 CI 工作流文件"
    workflow_text = "\n".join(path.read_text(encoding="utf-8") for path in workflow_files)

    assert ".python-version" in workflow_text, "CI 必须使用根目录 Python 版本声明"
    assert ".nvmrc" in workflow_text, "CI 必须使用根目录 Node.js 版本声明"
    assert re.search(r"uv\s+sync[^\n]*--frozen", workflow_text), (
        "CI 必须使用 uv sync --frozen"
    )
    assert "npm ci" in workflow_text, "CI 必须使用 npm ci"
    assert "uv run" in workflow_text, "CI Python 工具必须通过 uv run 启动"
    assert "npm run" in workflow_text, "CI 前端工具必须通过 npm run 启动"
