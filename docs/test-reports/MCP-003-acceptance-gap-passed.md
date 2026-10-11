# MCP-003 Acceptance Gap TEST_PASSED

- 状态：`TEST_PASSED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；隔离 PostgreSQL 17.11（端口 55439）；uv 0.7.21；Python 3.11.13
- 依据：`docs/test-reports/MCP-003-acceptance-gap-red.md`、`docs/acceptance/MCP-003.md`
- 黑盒声明：只使用公开 OAuth、独立 HTTP client、`/mcp` JSON-RPC、公开工具结果和公开应用查询；未读取或分析 `backend/apps/`、`backend/config/`，未修改生产代码或测试文件

## 验收缺口目标用例

### 过期 proposal

独立 pytest 进程：

```powershell
$env:MCP_TEST_EXPIRED_PROPOSAL_ID='prop_mcp_test_expired_fixture'
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_003_acceptance_gap.py::test_expired_proposal_can_be_checked_when_public_test_surface_is_available','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：`1 passed, 0 failed, 0 errors`

公开证据：apply 返回 `PROPOSAL_EXPIRED`，且不回显 proposal ID。

### 审计写入失败回滚

独立 pytest 进程：

```powershell
$env:MCP_TEST_AUDIT_FAILURE_MODE='1'
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_003_acceptance_gap.py::test_audit_failure_injection_rolls_back_when_public_test_surface_is_available','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：`1 passed, 0 failed, 0 errors`

公开证据：审计故障时 apply 失败，业务面试流程保持未写入；proposal 未被成功消费；响应包含审计失败语义且未泄露内部异常、SQL 或凭据。

### 补充专项正常模式

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_003_acceptance_gap.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：`2 passed, 2 skipped, 0 failed, 0 errors`

其中 2 项通过：

- 独立 HTTP client 创建 proposal、无协议 session 继续 apply，返回 `status=applied`。
- 成功、confirm=false、冲突、幂等重放的公开结果和敏感信息边界。

正常模式下的两个 skip 是因为该模式没有设置过期 fixture 和审计故障 fixture；两条用例已在上述独立环境进程中分别通过。

同时设置两个故障变量运行补充全量时得到 `2 failed, 2 passed`。失败来自审计故障模式预期地拦截同一文件中的两个正常成功路径，不是实现回归；目标故障用例已按要求独立通过，避免把强制故障配置下的正常成功断言误判为失败。

## MCP 回归

### MCP-003 全量

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_003.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：`12 passed, 0 failed, 0 errors`

### MCP-002 有效回归

排除被 MCP-003 五工具白名单取代的旧三工具列表断言：

```text
9 passed, 1 deselected, 0 failed, 0 errors
```

### MCP-001 有效回归

排除被新工具白名单取代的旧只读/未知工具断言：

```text
17 passed, 3 deselected, 0 failed, 0 errors
```

## APP 回归

```text
APP-009：25 passed, 0 failed, 0 errors
APP-010：21 passed, 0 failed, 0 errors
APP-011：24 passed, 0 failed, 0 errors
APP-012：5 passed, 0 failed, 0 errors
```

## 验收反馈对应证据

- [x] 无 session/独立 client：Client A preview、Client B apply，proposal 可验证并成功应用。
- [x] 成功 apply：返回 `audit_id` 和 applied 结果。
- [x] confirm=false：不写业务数据并返回失败结果。
- [x] 过期：测试 fixture 下返回 `PROPOSAL_EXPIRED`，不泄露 proposal ID。
- [x] 冲突：目标被直接修改后返回 `CONFLICT`，保留新数据。
- [x] 幂等重放：返回原 `audit_id` 和 `idempotent_replay=true`，不重复业务变更。
- [x] 参数冲突：MCP-003 原专项已验证同幂等键不同指纹拒绝，本轮 MCP-003 全量继续通过。
- [x] 审计失败回滚：故障模式下 apply 失败，业务数据和 proposal 成功应用状态均未形成。
- [x] 敏感信息边界：响应不包含 Access Token、授权码、Refresh Token、密码、SQL 或内部堆栈。

## 审计证据边界

公开契约不提供审计查询工具；因此黑盒可观察证据是成功结果中的 `audit_id`、失败/冲突/过期/重放的公开状态、业务回滚结果和脱敏响应。测试没有读取内部审计表，也没有把 `audit_id` 推断为完整内部字段查询证据。若项目管理验收要求逐字段核验 `before/after`、`user/sub`、`client_id`、`resource`、`request_id` 和幂等 hash，仍需单独批准一个当前用户隔离、脱敏的公开 `audit_evidence` 契约；本轮不修改生产接口来补造该能力。

## 结论

验收反馈要求的过期 proposal、审计失败原子回滚、独立 client 无状态路径、失败/冲突/重放结果和敏感信息边界均已有独立公开测试证据。MCP-003 全量、有效 MCP-002/MCP-001 回归及 APP-009/010/011/012 回归全部通过。

当前补充测试状态为 `TEST_PASSED`，交由项目管理 Agent重新验收。未修改生产代码、测试代码、任务单或验收记录。
