# MCP-001 TEST_PASSED

- 状态：`TEST_PASSED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；PostgreSQL 17.11（隔离端口 55439）；uv 0.7.21；Python 3.11.13
- 依赖：`uv sync --frozen --group test`，成功；未修改依赖声明或锁文件
- 生产实现：未读取、未分析、未修改 `backend/apps/`、`backend/config/`

## 测试夹具

MCP 成功路径现在完全通过公开 HTTP/JSON/JSON-RPC 建立：

1. `POST /api/v1/auth/register/` 创建两个隔离测试用户。
2. `POST /api/v1/auth/login/` 仅取得 Web JWT，用于通过公开应用 API 播种数据；该 JWT 未作为 OAuth/MCP Token 使用。
3. `GET /oauth/login` 读取公开登录表单和 CSRF hidden field。
4. `POST /oauth/login` 提交 username/password/next，确认 `sessionid` cookie 建立 Django OAuth session。
5. `POST /oauth/register` 为每个用户注册 public DCR client，取得 `client_id`。
6. `GET/POST /oauth/authorize` 完成公开授权和用户同意。
7. `POST /oauth/token` 使用授权码和 PKCE `S256` verifier 换取 `applications:read` access token。
8. 使用两个合法 OAuth Token 执行现代 MCP、`find_applications` 和跨用户隔离测试。

未使用 `MCP_TEST_ACCESS_TOKEN_A/B/FOREIGN_APPLICATION_ID`，未伪造 CIMD HTTPS metadata 成功流程。

## 命令与结果

语法检查：

```text
uv run python -m py_compile tests/test_mcp_001.py
通过
```

MCP-001 专项：

```powershell
& G:\job\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_001.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：`20 passed`。

必要回归：AUTH-002/003/004、APP-012、应用列表隔离相关测试结果为 `44 passed`。

## MCP-001 覆盖结果

| 范围 | 结果 |
|---|---|
| Protected Resource Metadata | 通过 |
| Authorization Server Metadata / CIMD advertised | 通过；CIMD 成功联调仍需真实 HTTPS metadata 环境，未伪造成功断言 |
| DCR public registration | 通过，返回 201 和 `client_id` |
| OAuth Django session login | 通过，公开 `/oauth/login` form POST 建立 `sessionid` |
| Authorization Code + PKCE `S256` | 通过，公开 authorize/token 链路取得 `applications:read` Token |
| redirect/resource/scope/非法 code 拒绝 | 通过 |
| MCP 2026-07-28 `server/discover` | 通过，不依赖 `initialize` |
| `/mcp` Bearer 认证、Web JWT 边界、资源受众错误 | 通过 |
| `tools/list` 白名单 | 通过，仅暴露 `find_applications`，schema 含定位/筛选/分页且标记只读 |
| `find_applications` | 通过，返回 `content`、`structuredContent` 和 APP-012 聚合结构 |
| `user_id` 越权参数 | 通过拒绝 |
| 双用户隔离 | 通过，另一用户查询返回空结果，所有者可查询自己的记录 |
| stateless/no protocol session | 通过，现代请求不要求 `Mcp-Session-Id` |
| 2025-11-25 legacy handshake | 通过，`initialize`、`notifications/initialized` 和后续 `tools/list` 可完成 |
| 未知工具/未知方法 | 通过 JSON-RPC 错误 |

## 测试侧修正

- 将模块数据库夹具设为 `django_db(transaction=True)`，支持公开 OAuth/DCR 多请求链路和 MCP 请求之间的真实事务边界。
- 修正一个测试自身的误报：跨用户空结果不再对整个 JSON-RPC 文本搜索短数字 ID，而是只断言结构化 `results` 为空；没有放宽数据隔离契约。

以上均为测试夹具/测试断言修正，未修改生产代码、业务实现或依赖。

## 结论与交接

核心成功路径不再 skipped，MCP 专项和必要回归全部通过。当前状态为 `TEST_PASSED`，交由项目管理 Agent 进行逐条验收。

## 黑盒声明

本次复测只通过公开 HTTP/JSON/JSON-RPC 输入输出和公开数据库可观察结果判断；未读取或分析生产实现代码，未修改生产代码或运行时依赖。

