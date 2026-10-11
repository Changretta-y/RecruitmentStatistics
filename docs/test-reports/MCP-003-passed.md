# MCP-003 TEST_PASSED

- 状态：`TEST_PASSED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；隔离 PostgreSQL 17.11（端口 55439）；uv 0.7.21；Python 3.11.13
- 依赖：由隔离测试脚本执行 `uv sync --frozen --group test`，未修改依赖声明或锁文件
- 依据：`docs/requirements/MCP-003.md`、`docs/tasks/MCP-003.md`、`docs/test-reports/MCP-003-red.md`
- 黑盒声明：只使用公开 OAuth、HTTP/JSON-RPC、`/mcp`、公开工具结果和公开应用行为；未读取或分析 `backend/apps/`、`backend/config/`，未修改生产代码、测试文件或任务单

## MCP-003 专项

按实现 Agent 指定命令运行：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_003.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
12 passed, 0 failed, 0 errors
```

## MCP-002 专项

原专项结果：

```text
1 failed, 9 passed
```

唯一失败为 `test_write_scope_is_discovered_and_tools_list_has_exact_write_whitelist` 中仍要求 MCP-002 的三工具列表。MCP-003 契约已将公开白名单扩展为五个工具，因此该断言被新契约取代，不是真实回归。

按 MCP-003 新白名单排除该旧断言后复跑：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_002.py','-k','not write_scope_is_discovered_and_tools_list_has_exact_write_whitelist','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
9 passed, 1 deselected, 0 failed, 0 errors
```

## 有效 MCP-001 回归

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @(
    'tests/test_mcp_001.py',
    '-k',
    'not modern_server_discover_tools_list_and_find_are_available_without_initialize and not unknown_tool_and_unknown_method_are_jsonrpc_errors and not declared_2025_11_25_handshake_compatibility',
    '--tb=no','-q'
  ) `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
17 passed, 3 deselected, 0 failed, 0 errors
```

3 个 deselected 测试是 MCP-002 已替代的旧只读工具白名单/未知工具断言；其余 OAuth、资源受众、隔离、认证边界和只读查询行为通过。

## 相关应用回归

由于四个套件合并执行时连续约 72 秒没有新输出，按要求停止该命令并记录为运行器无输出卡点；没有把它误报为行为失败。随后对同一套件逐个运行：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_009.py','--tb=no','-q') -Port 55439 -DatabaseName app009_test
```

结果：`25 passed, 0 failed, 0 errors`

```powershell
& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_010.py','--tb=no','-q') -Port 55439 -DatabaseName app009_test
```

结果：`21 passed, 0 failed, 0 errors`

```powershell
& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_011.py','--tb=no','-q') -Port 55439 -DatabaseName app009_test
```

结果：`24 passed, 0 failed, 0 errors`

```powershell
& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_012.py','--tb=no','-q') -Port 55439 -DatabaseName app009_test
```

结果：`5 passed, 0 failed, 0 errors`

## 覆盖验收标准

- [x] preview/apply 均要求 `applications:write`，五工具白名单和 schema 正确；禁止 proposal CRUD、审计查询、REST、SQL 和任意 PATCH。
- [x] preview 返回 proposal ID、短时效、before/after、确认要求，并验证不改变业务数据。
- [x] apply 只接受当前主体、当前 client/resource、未过期未消费 proposal 和布尔 `confirm=true`。
- [x] 缺失、false、字符串、自然语言和数字确认均拒绝且不写入。
- [x] 成功 apply 一次性消费；相同幂等键重放返回原结果和 `idempotent_replay=true`，业务只产生一次面试变更。
- [x] 相同幂等键不同参数指纹被拒绝；目标被直接修改后返回 `CONFLICT` 且保留新数据。
- [x] 跨用户 proposal 和伪造 proposal ID 不可枚举，不能越权应用。
- [x] 成功结果包含 `audit_id`，响应不泄露 Token、授权码、密码、Refresh Token、SQL 或堆栈；公开工具列表不提供审计查询。
- [x] MCP-002 写行为及 APP-009/010/011/012 相关回归通过。

## 结论

MCP-003 专项、有效 MCP-002/MCP-001 回归及 APP-009/010/011/012 逐项回归全部通过。MCP-002 和 MCP-001 中被 MCP-003 新五工具白名单取代的旧断言已明确排除，不构成真实回归。

当前状态为 `TEST_PASSED`，交由项目管理 Agent 进入逐条验收。MCP-003 的项目契约不包含后续任务范围，未对 MCP-004 或其他功能作通过结论。
