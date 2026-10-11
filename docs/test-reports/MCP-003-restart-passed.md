# MCP-003 Real HTTP Restart / Multi-Process TEST_PASSED

- 状态：`TEST_PASSED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；Python 3.11.13；uv 0.7.21；隔离 PostgreSQL 17.11（端口 55439，数据库 `app009_test`）
- 测试文件：[backend/tests/test_mcp_003_real_restart.py](../../backend/tests/test_mcp_003_real_restart.py)
- 允许修改：仅测试目录和测试报告

## 执行命令

隔离数据库迁移检查：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -MigrateOnly -Port 55439 -DatabaseName app009_test
```

结果：`No migrations to apply.`

真实 HTTP 重启测试：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_003_real_restart.py','--tb=no','-q','-s') `
  -Port 55439 -DatabaseName app009_test
```

结果：`1 passed in 16.28s`，`0 failed`，`0 errors`。

## 黑盒生命周期证据

1. 服务 A 以独立 uvicorn 进程启动，公开 OAuth 注册、登录、DCR、Authorization Code + PKCE 和 Bearer Token 流程成功。
2. 服务 A 通过公开 `/mcp` 创建投递，并通过 `preview_application_change` 返回 proposal ID：`prop_af7de9e9d58841f3818c4eb4d7e62310`。
3. 服务 A 停止后，服务 B 以不同端口和全新进程启动；不复用 MCP 协议 session，使用同一 Bearer Token 调用 apply，返回：
   - `status: applied`
   - 相同 `proposal_id`
   - 非空 `audit_id: audit_6669fda6557b46e29573f15dd9a58d3c`
4. 服务 C 以第三个端口并行启动；使用无 Cookie 的独立 HTTP 请求重放同一 apply，返回：
   - `status: applied`
   - `idempotent_replay: true`
   - 与 B 相同的 `audit_id`
5. 服务 C 随后通过 `find_applications` 读取业务结果，确认二面名称为“二面”、时长为 60 分钟。
6. 全部服务进程均进入清理路径；测试期间未出现 `Task group is not initialized`，所有 MCP 成功响应均包含公开 `structuredContent`。

## 结论

真实服务 A→B 重启、B→C 多进程等价请求、无会话 Bearer apply、幂等重放和业务读取均独立通过。该报告闭合 MCP-003 验收记录中“服务重启/多副本”剩余证据缺口。

## 其余回归命令状态

已启动但按用户要求中止的长回归命令：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @(
    'tests/test_mcp_003.py',
    'tests/test_mcp_002.py',
    'tests/test_mcp_001.py',
    'tests/test_app_009.py',
    'tests/test_app_010.py',
    'tests/test_app_011.py',
    'tests/test_app_012.py',
    '--deselect', 'tests/test_mcp_002.py::test_write_scope_is_discovered_and_tools_list_has_exact_write_whitelist',
    '--deselect', 'tests/test_mcp_001.py::test_modern_server_discover_tools_list_and_find_are_available_without_initialize',
    '--deselect', 'tests/test_mcp_001.py::test_unknown_tool_and_unknown_method_are_jsonrpc_errors',
    '--deselect', 'tests/test_mcp_001.py::test_declared_2025_11_25_handshake_compatibility',
    '--tb=no', '-q'
  ) `
  -Port 55439 -DatabaseName app009_test
```

该命令在用户要求停止时仍在运行，已发送中断，未取得最终汇总；不将其标记为通过或失败。

此前未过滤旧契约断言的组合回归已结束：`113 passed`、`4 failed`。4 个失败均为已知的旧 MCP-001/MCP-002 白名单或旧握手断言，与当前五工具新契约冲突；APP-009/010/011/012 与 MCP-003 未报告失败。

本次测试 Agent 未读取或分析 `backend/apps/`、`backend/config/` 生产实现，未修改生产代码、依赖、任务单或验收记录。
