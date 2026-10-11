# MCP-002 RED

- 状态：`RED_CONFIRMED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；PostgreSQL 17.11（隔离端口 55439）；uv 0.7.21；Python 3.11.13
- 依赖同步：由 `run-isolated-postgres.ps1` 执行 `uv sync --frozen --group test`，成功；未修改依赖声明或锁文件
- 测试文件：`backend/tests/test_mcp_002.py`
- 生产实现：未读取、未搜索、未枚举或分析 `backend/apps/`、`backend/config/`；未修改生产代码

## 命令与结果

语法检查：

```text
Set-Location backend; uv run --no-sync python -m py_compile tests/test_mcp_002.py
通过
```

MCP-002 新增专项（隔离 PostgreSQL，完整输出使用 `--tb=no`）：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_002.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
10 failed, 0 passed, 0 errors
```

MCP-001 必要回归：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_001.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
20 passed, 0 failed, 0 errors
```

## RED 证据

失败由 MCP-002 尚未提供的公开行为引起，不是语法、夹具、数据库或依赖环境错误：

1. 请求 `applications:read applications:write` 的公开 OAuth 授权被稳定返回 `invalid_scope`，响应明确为 `Only applications:read is supported.`；因此 write scope 尚未进入授权和 token 契约。为继续验证其余 HTTP/JSON-RPC 断言，测试 fixture 在确认该特定公开错误后使用真实的 read-only OAuth token 回退，未生成或伪造内部 token。
2. `tools/list` 仍只提供 `find_applications`，缺少 `create_application` 和 `upsert_application_stage`。
3. 以 read-only token 调用写工具未在 HTTP 层返回 `403 insufficient_scope`。
4. 写工具调用返回公开的 `Unknown tool`，因此无法创建/复用公司、追加或去重岗位，也无法新增/更新/清空测评、笔试和面试阶段。
5. 非法输入、跨用户目标、伪造用户字段和一致性冲突无法进入对应写工具的字段级错误、404 隔离和原子性契约；测试明确排除仅返回 `Unknown tool` 的结果，避免把未知工具误判为业务校验通过。

新增测试连续运行结果稳定为同一失败集合：`10 failed, 0 passed, 0 errors`。MCP-001 回归独立通过 `20 passed`，说明 OAuth 基础链路、数据库夹具和现有只读 MCP 服务未发生回归。

## 覆盖的公开行为

`test_mcp_002.py` 通过公开 OAuth/HTTP/JSON-RPC 和公开 REST setup 覆盖：

- Authorization Server Metadata 与 Protected Resource Metadata 同时声明 `applications:read`、`applications:write`。
- Authorization Code + PKCE `S256` 请求 write scope；read-only token 调用写工具必须得到 HTTP `403 insufficient_scope`。
- `tools/list` 精确白名单：`find_applications`、`create_application`、`upsert_application_stage`；只读/写标记和完整关键 schema。
- 新公司投递：公司名称、职位、带时区投递时间、八值状态、notes、来源描述、`content` 与 `structuredContent`。
- 已有公司复用、同一用户追加岗位、重复岗位的确定性行为；不创建重复聚合。
- 缺失公司定位、非法状态、无时区时间、岗位级招聘 URL、空职位、伪造 `user_id` 的字段级拒绝和失败无部分写入。
- 共享 `assessment`、`written_test` 阶段新增、更新、清空、时长更新及 `application_status` 保留。
- 岗位 `interview` 的 first/second/third/hr/other 轮次、自定义名称、新增、更新、清空及岗位目标。
- 非法阶段、非法时间、非正时长、错误岗位目标的拒绝和失败原子性。
- 双用户跨用户 `application_id`/`position_id` 隔离、禁止 `user_id` 越权、公开结构化聚合不泄露用户字段。
- 公司 ID/名称不一致时拒绝并保持原岗位集合不变。

## 交接建议

交由功能实现 Agent，状态进入 `IMPLEMENTING`。请按 MCP-002 公开契约先实现：

1. write scope 的 discovery、授权同意和 Resource Server `403 insufficient_scope`。
2. 三工具白名单、完整 JSON Schema 与写操作标记。
3. `create_application` 的 APP-012 公司复用/岗位追加/重复确定性结果。
4. `upsert_application_stage` 的 APP-011 阶段映射、时间/时长校验、清空、current_stage 投影与保存状态解耦。
5. 当前用户隔离、字段级错误、404 语义和事务原子性。

实现完成后保持测试目录只读，提交 `READY_FOR_TEST`，由测试 Agent 使用同一命令独立复测并产出 `MCP-002-passed.md` 或 `TEST_FAILED` 报告。

## 黑盒声明

本阶段只依据 MCP-002、MCP-001、APP-011、APP-012 的公开契约，通过公开 OAuth、HTTP/JSON-RPC、公开 REST setup 和可观察结构化结果编写/运行测试；未读取或分析生产实现代码，未修改生产代码、运行时依赖、任务单或测试质量门槛。
