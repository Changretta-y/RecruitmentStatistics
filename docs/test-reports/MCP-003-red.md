# MCP-003 RED

- 状态：`RED_CONFIRMED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；PostgreSQL 17.11（隔离端口 55439）；uv 0.7.21；Python 3.11.13
- 依赖同步：由 `run-isolated-postgres.ps1` 执行 `uv sync --frozen --group test`，成功；未修改依赖声明或锁文件
- 测试文件：`backend/tests/test_mcp_003.py`
- 生产实现：未读取、未搜索、未枚举或分析 `backend/apps/`、`backend/config/`；未修改生产代码

## 命令与结果

语法检查：

```text
Set-Location backend; uv run --no-sync python -m py_compile tests/test_mcp_003.py
通过
```

MCP-003 新增专项（隔离 PostgreSQL，使用公开 OAuth 和 `/mcp` JSON-RPC）：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_003.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
12 failed, 0 passed, 0 errors
```

失败不是 OAuth fixture、数据库连接、语法或环境问题。MCP-002 的 `applications:write` OAuth 流程已通过公开授权链路取得有效写 Token，业务目标也通过已验证的 `create_application` 建立；失败请求均真实发送到 `/mcp`，返回的公开错误为：

```text
Unknown tool: preview_application_change
Unknown tool: apply_application_change
```

单例复核：`test_preview_returns_short_lived_proposal_diff_and_does_not_change_business_data` 稳定在 proposal 工具调用断言处失败，未发生夹具或环境错误。

## RED 证据

当前 MCP-002 实现尚未提供 MCP-003 的两个工具，因此以下安全闭环行为均缺失：

1. `tools/list` 尚未增加 `preview_application_change` 和 `apply_application_change`，也无法验证五工具精确白名单和 schema。
2. `applications:read` Token 调用 preview 未在 HTTP 层返回 `403 insufficient_scope`。
3. preview 无法生成持久化、短时效 proposal、before/after 差异、警告和 `confirmation_required=true`，也无法验证 preview 不改变业务数据。
4. apply 无法验证 `confirm` 必须是 JSON 布尔 `true`，以及缺失、false、字符串、自然语言和数字确认均不写入。
5. apply 无法验证单次消费、相同幂等键重放原结果、重复成功不产生第二次业务变更和第二条成功审计。
6. 无法验证相同幂等键不同参数指纹的冲突拒绝、proposal 过期/失效拒绝和目标变化后的 `CONFLICT`。
7. 无法验证 proposal 的用户、OAuth client、resource 绑定及跨用户不可枚举错误。
8. 无法验证成功结果的 `audit_id`、before/after/user/request/idempotency 审计语义和敏感凭据脱敏。

失败稳定地落在缺少工具行为，而非测试前置条件；符合从 `RED_CONFIRMED` 进入实现阶段的门禁。

## 覆盖的公开行为

`test_mcp_003.py` 只通过 MCP-002 已验证的公开 OAuth fixture、HTTP/JSON-RPC 和公开工具结果覆盖：

- preview/apply 的 write scope、五工具白名单、语义化 schema，以及禁止 proposal CRUD、审计查询、REST、SQL 和任意 PATCH。
- preview 的目标、结构化 `upsert_application_stage` change、proposal ID、状态、短 TTL、before/after 和不落业务数据。
- apply 的显式布尔确认、错误确认值不写入。
- 成功应用的一次性消费、原结果 replay 标记、同幂等键重放和单次业务变更。
- 同幂等键不同参数指纹冲突。
- preview 后直接变更目标时的冲突拒绝和新数据保留。
- 跨用户/跨 client proposal、伪造 proposal ID 的不可枚举错误。
- 成功应用返回审计标识，并检查响应不含 Access Token、授权码、密码、Refresh Token、SQL 或未知审计查询能力。

审计的内部字段（before/after、user/sub、client、resource、request_id、幂等安全标识）没有公开查询接口；测试按契约只验证成功结果中的 `audit_id`、工具白名单不暴露审计 CRUD、响应不泄露 secret。是否实际持久化这些字段需由实现后的公开副作用或项目管理验收进一步确认，测试不读取生产数据库内部表。

## 交接建议

交由功能实现 Agent，状态进入 `IMPLEMENTING`。请按 MCP-003 公开契约实现：

1. `preview_application_change` 和 `apply_application_change` 的 write scope、工具 schema 和精确白名单。
2. 数据库持久化 proposal、短时效、用户/client/resource 绑定和无 session 可验证性。
3. preview 的规范化差异和不改业务数据；apply 的 `confirm=true`、原状态指纹和一次性消费。
4. 幂等键重放、参数指纹冲突、过期/已消费错误和目标冲突保护。
5. 成功/失败/冲突/过期/重放审计，包含契约要求的上下文与脱敏 before/after，审计失败不得形成无记录成功。

实现完成后保持本测试文件只读，提交 `READY_FOR_TEST`，由测试 Agent 使用同一命令独立复测。

## 黑盒声明

本阶段只依据 `docs/requirements/MCP-003.md`、`docs/tasks/MCP-003.md`、MCP-002/MCP-001 公开契约和公开行为测试编写、运行测试；未读取或分析生产实现代码，未修改生产代码、运行时依赖、任务单或测试质量门槛。
