# TASK-001 实现说明

## 实现范围

- 在 `backend/` 建立独立的 uv Python 项目，避免继承仓库上级 uv workspace。
- 使用最小 Django 配置启动后端，不注册业务应用、不引入数据库迁移或业务数据依赖。
- 通过 `backend.config.urls` 暴露 `GET /api/v1/health/`。
- 健康接口仅接受 GET：成功响应为 HTTP 200、`application/json`，严格 JSON `{"status":"ok"}`；其他方法由 Django 的 `require_GET` 返回 405。

## 架构

- `backend/manage.py`：Django 管理命令入口。
- `backend/config/`：项目设置、根 URL 和 WSGI 入口。
- `backend/apps/health/`：健康检查应用及公开 URL。
- `backend/pyproject.toml`：backend 独立 uv 项目声明，运行时仅依赖 Django，测试依赖置于 `test` 依赖组。

## uv 命令

在仓库根目录执行：

```powershell
uv lock --project backend
uv run --project backend --group test pytest backend/tests -q
```

如需从 backend 目录执行：

```powershell
uv lock
uv run --group test pytest tests -q
```

## 验证方式

验证覆盖 TASK-001 的公开契约：GET 成功状态、JSON 内容类型、严格响应体和 POST 405。实现 Agent 只运行既有测试，不修改 `backend/tests/` 或 `docs/test-reports/`。
