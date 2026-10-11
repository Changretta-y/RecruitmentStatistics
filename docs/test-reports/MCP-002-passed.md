# MCP-002 TEST_PASSED

- 状态：`TEST_PASSED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；PostgreSQL 17.11（隔离端口 55439）；uv 0.7.21；Python 3.11.13
- 依赖：通过项目隔离测试脚本执行 `uv sync --frozen --group test`，未修改依赖声明或锁文件
- 依据：`docs/requirements/MCP-002.md`、`docs/tasks/MCP-002.md`、`docs/test-reports/MCP-002-red.md`
- 测试文件：`backend/tests/test_mcp_002.py`
- 黑盒边界：仅使用公开 OAuth、HTTP/JSON-RPC、公开 REST setup、响应和数据库可观察结果；未读取或分析 `backend/apps/`、`backend/config/` 生产实现，未修改测试质量门槛或生产代码

## 测试命令与结果

### MCP-002 专项

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_002.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
10 passed, 0 failed, 0 errors
```

### MCP-001 回归

完整原套件结果为：

```text
3 failed, 17 passed
```

3 个失败均为 MCP-001 中被 MCP-002 新契约明确替代的旧断言：

- `tools/list` 仍要求只返回 `find_applications`；MCP-002 要求新增两个写工具。
- 将 `create_application` 作为未知工具；MCP-002 要求该工具公开可用。
- 2025-11-25 兼容握手后的工具列表仍要求只返回 `find_applications`；MCP-002 同样要求三工具白名单。

按新契约排除上述 3 个测试后，复跑命令为：

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

其余 MCP-001 OAuth、资源受众、用户隔离、现代协议、认证边界和只读查询行为均保持通过。

### 相关应用回归

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_app_011.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：`24 passed, 0 failed, 0 errors`

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_app_012.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：`5 passed, 0 failed, 0 errors`

补充 APP-012 依赖的 APP-009/APP-010 聚合与兼容回归：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_app_009.py','tests/test_app_010.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：`46 passed, 0 failed, 0 errors`

## 覆盖验收标准

- [x] OAuth Metadata 支持 `applications:write`；授权可取得读写 Token；read-only Token 调用写工具被拒绝。
- [x] `tools/list` 精确暴露 `find_applications`、`create_application`、`upsert_application_stage`，并提供读写语义和关键输入 schema。
- [x] `create_application` 支持新公司、公司复用、追加岗位和重复岗位确定性结果；返回可读 `content` 与公开 `structuredContent`。
- [x] 创建参数覆盖公司定位、八值状态、带时区时间、notes、来源描述；非法状态、无时区时间、岗位级招聘 URL、空岗位和伪造用户字段被拒绝且无部分写入。
- [x] `upsert_application_stage` 支持 assessment、written_test 及 first/second/third/hr/other interview 的新增、更新和清空。
- [x] 阶段时间/时长校验、时区规范化、错误目标隔离、失败原子性和结构化结果通过。
- [x] 流程更新后 `current_stage` 正确投影，保存的 `application_status` 不被隐式修改。
- [x] 双用户只能访问和写入自己的投递/岗位/流程；不能通过 `user_id` 或跨用户 ID 越权。
- [x] 未实现 preview/apply、proposal、幂等和审计能力；本报告未将 MCP-003 范围纳入 MCP-002 通过结论。

## 结论与交接

MCP-002 公开行为专项及 APP-011/APP-012 相关回归均通过。MCP-001 的 3 个失败属于已被 MCP-002 新契约取代的旧断言，不构成真实回归；有效 MCP-001 回归通过 `17/17`。

当前测试状态为 `TEST_PASSED`，交由项目管理 Agent 进行逐条验收。项目管理 Agent 可根据 MCP-002 任务单进入 `ACCEPTING`；不得将本报告解释为 MCP-003 的 preview/apply、幂等、冲突检测或审计已完成。
