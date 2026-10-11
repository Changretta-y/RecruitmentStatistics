# MCP-003 Acceptance Gap RED

- 状态：`RED_CONFIRMED`（验收证据缺口；不是现有公开业务行为失败）
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；隔离 PostgreSQL 17.11（端口 55439）；uv 0.7.21；Python 3.11.13
- 依据：`docs/acceptance/MCP-003.md` 及 MCP-003/MCP-002 公开行为契约
- 新增测试：`backend/tests/test_mcp_003_acceptance_gap.py`
- 生产实现：未读取、未搜索、未枚举或分析 `backend/apps/`、`backend/config/`；未修改生产代码

## 命令与结果

语法检查：

```text
Set-Location backend; uv run --no-sync python -m py_compile tests/test_mcp_003_acceptance_gap.py
通过
```

补充专项：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_003_acceptance_gap.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
2 passed, 2 skipped, 0 failed, 0 errors
```

## GREEN 证据

### 独立 HTTP client / 无协议 session

`test_proposal_survives_independent_http_clients_without_protocol_session` 通过：

1. Client A 通过公开 `/mcp` 创建投递并生成 proposal。
2. Client B 使用同一合法 OAuth Token、没有复用 Client A 的 cookie 或 MCP session，调用 apply。
3. apply 成功，返回 `status=applied`。

该结果证明 proposal 应用不依赖上一次 HTTP 请求的客户端对象或协议 session。当前测试环境是单个 Django 测试进程，未声称完成真实进程重启或多副本网络路由验证。

### 公开结果、重放、失败和敏感信息边界

`test_public_results_cover_audit_id_and_redaction_for_success_replay_failure_and_conflict` 通过：

- 成功 apply 返回 `audit_id`。
- 相同 proposal/幂等键重放返回 `idempotent_replay=true`，并复用同一 `audit_id`。
- `confirm=false` 返回错误，不应用变更。
- preview 后直接修改目标，再 apply 返回 `CONFLICT`。
- 冲突响应不包含 Access Token、授权码、Refresh Token、密码或 SQL 字符串。

这些是当前公开响应可观察到的 GREEN 证据；它们不能替代审计存储内部字段的查询证据。

## RED 覆盖缺口

### 1. 过期 proposal 无公开可控测试入口

`test_expired_proposal_can_be_checked_when_public_test_surface_is_available` 被跳过，原因是当前公开契约没有：

- 创建指定已过期 proposal 的公开接口；
- 仅测试环境可用的 proposal TTL/clock 控制；
- 可公开注入且不修改生产数据的时间推进入口。

最小必要测试夹具：提供仅测试环境的 `MCP_TEST_EXPIRED_PROPOSAL_ID`，其对应 proposal 在测试数据库中已过期；或提供仅测试环境的短 TTL/clock 控制。夹具必须通过公开 MCP 请求使用，不能直接导入模型、修改内部表或伪造 Token。

### 2. 审计写入失败无公开故障注入入口

`test_audit_failure_injection_rolls_back_when_public_test_surface_is_available` 被跳过，原因是当前公开契约没有：

- 仅测试环境的审计写入失败开关；
- 可替换的公开审计 sink；
- 可观察的审计存储故障注入配置。

最小必要测试夹具：提供仅测试环境的 `MCP_TEST_AUDIT_FAILURE_MODE=1`，使 audit write 明确失败。测试应通过公开 `/mcp` 完成 preview/apply，并观察：

- apply 返回 `isError=true` 或明确审计失败码；
- 业务阶段数据保持未应用；
- proposal 不被消费；
- 不产生无审计成功；
- 响应不泄露内部异常、SQL 或凭据。

不得为此修改生产代码、生产配置或绕过公开 MCP 接口读取审计表。

### 3. 审计各失败状态的可查询证据不足

当前公开工具白名单明确不提供审计查询工具；公开 apply 成功结果只提供 `audit_id`，失败/冲突/过期/重放结果没有公开审计事件查询接口。因此本轮可以验证响应状态、幂等行为和脱敏边界，但不能独立证明以下审计字段已经持久化：

```text
before/after
user/sub
client_id
resource
request_id
idempotency_key_hash
failure/conflict/expired/replay 状态
```

若项目要求黑盒独立验证上述字段，最小必要契约应增加只读、当前用户隔离、脱敏的审计证据查询能力，或让每次工具结果返回受限的 `audit_evidence` 摘要；不能把生产数据库内部表作为测试公开接口。

## 结论与交接

本轮没有发现现有 MCP-003 成功路径、独立 client 无 session 路径或公开响应脱敏边界的行为回归；相关 GREEN 证据已记录。

但验收记录要求的“过期状态审计证据”和“审计写入失败时业务/ proposal 原子回滚”目前没有公开测试入口，因此仍不能据此将 MCP-003 的验收状态改为 `DONE`。本报告将状态标记为 `RED_CONFIRMED`，退回项目管理 Agent 决定是否补充测试专属配置/公开契约；测试 Agent 未修改生产代码来制造入口。

## 黑盒声明

本报告只使用公开 OAuth、公开 `/mcp` JSON-RPC、独立 Django HTTP client 和可观察响应；未读取或分析生产实现，未直接读取审计表，未修改生产代码、运行时依赖、任务单或验收记录。
