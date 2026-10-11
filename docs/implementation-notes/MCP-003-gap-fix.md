# MCP-003 验收缺口回流实现说明

- 状态：`READY_FOR_TEST`
- 角色：功能实现 Agent
- 范围：仅补足验收缺口；未修改测试、测试报告、任务单或验收记录。

## 本次修复

### 仅测试环境的过期夹具

- `MCP_TEST_EXPIRED_PROPOSAL_ID` 仅在非生产配置下生效。
- 当测试通过公开 `apply_application_change` 使用该 ID 时，服务会在数据库中惰性建立一个绑定当前 OAuth 用户、client 和 resource 的已过期 proposal，并继续走正常的用户隔离、过期状态转换和审计路径。
- 夹具不绑定任何业务目标；响应只返回 `PROPOSAL_EXPIRED` 和受限 `audit_evidence`，不回显 proposal ID。
- `MCP_TEST_PROPOSAL_TTL_SECONDS` 可在非生产测试进程中将 proposal TTL 调低到 1–900 秒；生产仍使用 `MCP_PROPOSAL_TTL_SECONDS` 的 60–900 秒约束。
- `DJANGO_ENV=production` 时，以上两个测试配置被强制忽略，不会启用测试夹具或短 TTL。

### 审计故障注入与事务回滚

- 非生产进程设置 `MCP_TEST_AUDIT_FAILURE_MODE=1` 后，`apply_application_change` 的审计写入会明确失败；preview 审计仍可写入，以便测试通过公开流程创建 proposal。
- apply 的业务写入、proposal 消费、幂等记录和成功审计都在同一 `transaction.atomic()` 中；审计失败会回滚整个事务，并返回 `AUDIT_WRITE_FAILED`。
- 故障路径不会再启动一个独立的补偿审计事务，避免产生“无审计成功”或部分消费。
- 生产环境即使意外继承该环境变量也不会启用注入。

### 受限审计证据

- 成功、重放、冲突、过期、确认失败和事务失败结果均提供受限 `audit_evidence`：`audit_id`、`outcome`、`recorded`，失败时追加稳定 `failure_code`。
- 成功结果继续保留原 `audit_id`；成功重放继续复用原 `audit_id` 和 `idempotent_replay=true`，同时将证据摘要标为 `replay`，不改变既有 MCP-003 客户端契约。
- 错误结果通过 `CallToolResult.structuredContent` 返回摘要；不包含 proposal ID、Token、授权码、密码、邮箱全文、SQL 或堆栈。
- 审计记录继续保存完整的 request、subject、client/resource、tool/operation、proposal、幂等键哈希、目标、变更字段、脱敏前后摘要、结果和失败码字段。

## 自检

环境：Python 3.11.13、uv 0.7.21、隔离 PostgreSQL 17.11（端口 55439）。

```text
python -m py_compile apps/mcp/tools.py apps/mcp/views.py apps/mcp/server.py config/settings.py 通过
ruff check apps/mcp config/settings.py 通过
manage.py check 通过
manage.py makemigrations --check --dry-run 无迁移变更
隔离 PostgreSQL migrate 无迁移需要应用
MCP-003 专项：12 passed
过期夹具公开 MCP 用例：1 passed
审计故障注入公开 MCP 用例：1 passed
```

独立测试 Agent 仍需在进程重启/多副本等价请求、失败状态审计字段和故障回滚场景下复测，并产生新的 `TEST_PASSED` 报告；本说明不替代独立复测或项目管理验收。

建议复测环境变量：

```powershell
$env:MCP_TEST_EXPIRED_PROPOSAL_ID = 'prop_mcp_test_expired_fixture'
$env:MCP_TEST_AUDIT_FAILURE_MODE = '1'
```

两类开关应在不同的测试进程中启用；完成后清理环境变量。
