# MCP-001 TEST_FAILED

- 状态：`TEST_FAILED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；PostgreSQL 17.11（隔离端口 55439）；uv 0.7.21；Python 3.11.13
- 依赖：`uv sync --frozen --group test`，成功；未修改依赖声明或锁文件
- 生产实现：未读取、未分析、未修改 `backend/apps/`、`backend/config/`

## 本阶段测试变更

仅修改 `backend/tests/test_mcp_001.py` 测试夹具与调用方式：

- 通过公开 `/api/v1/auth/register/` 和 `/api/v1/auth/login/` 创建两个测试用户并建立公开登录边界。
- 通过公开 `POST /oauth/register` 动态注册两个公共客户端。
- 使用公开 `/oauth/authorize`、登录/同意页面和 `/oauth/token` 完成 Authorization Code + PKCE `S256`，预期取得 `applications:read` Token。
- 用公开应用 API 为两个用户播种隔离投递数据。
- 将生成的 Token 注入 `server/discover`、`tools/list`、`tools/call`、`find_applications` 和双用户隔离测试。
- 移除了 `MCP_TEST_ACCESS_TOKEN_A/B/FOREIGN_APPLICATION_ID` 及其他外部 Token 依赖。
- 保留 CIMD 能力声明测试；未伪造 HTTPS CIMD metadata 成功流程。
- 增加已声明兼容的 `2025-11-25` `initialize`/`notifications/initialized` handshake 测试。

未修改生产代码、现有测试断言的业务含义或测试质量门槛。

## 命令与结果

语法检查：

```text
uv run python -m py_compile tests/test_mcp_001.py
通过
```

MCP 专项：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_001.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
14 passed, 6 errors
```

14 项既有公开发现、认证边界、PKCE/资源错误和拒绝行为通过。6 项成功路径在 DCR fixture setup 阶段统一失败：

- `server/discover` 现代成功路径
- `tools/list` 白名单
- `find_applications` 结构与越权参数
- 双用户 `find_applications` 隔离
- stateless/no protocol session 成功路径
- 声明的 `2025-11-25` legacy handshake

## 失败证据

黑盒 fixture 对公开端点发送了标准 DCR JSON 请求：

```text
POST /oauth/register
Content-Type: application/json
grant_type: authorization_code
response_type: code
token_endpoint_auth_method: none
redirect_uris: [精确 HTTPS callback]
```

公开端点返回 HTTP `500`，因此无法得到 `client_id`，后续公开 authorize/login/token 和合法 MCP access token 无法开始。该失败发生在应用数据播种和 MCP 工具调用之前，不能归因于测试数据、模型访问或断言。

由于 DCR 是实现说明中声明启用的公共兼容入口，本错误阻塞了本地自动建立 OAuth fixture；不能把这些成功路径重新标记为 skipped，也不能使用伪造 Token 绕过。

## 按协议范围记录

| 范围 | 结果 |
|---|---|
| Protected Resource Metadata | 通过 |
| Authorization Server Metadata / CIMD advertised | 通过；未伪造 CIMD HTTPS metadata 成功联调 |
| PKCE `S256`、redirect、resource、scope 错误拒绝 | 通过 |
| `/mcp` 未认证、无效 Bearer、错误 scheme、Web JWT 边界 | 通过 |
| public DCR → authorize/login → token | 失败：`POST /oauth/register` 返回 500 |
| 现代 `server/discover` | 未执行成功调用，因 DCR fixture 被阻塞 |
| `tools/list` 白名单 | 未执行成功调用，因 DCR fixture 被阻塞 |
| `find_applications` APP-012 结构/只读 | 未执行成功调用，因 DCR fixture 被阻塞 |
| 双用户 OAuth 数据隔离 | 未执行成功调用，因 DCR fixture 被阻塞 |
| `2025-11-25` handshake | 未执行成功调用，因 DCR fixture 被阻塞 |

## 必要回归

此前同一隔离实现状态下的 AUTH-002/003/004、APP-012 和应用列表隔离回归为 `44 passed`。本轮只改动 MCP 测试夹具；DCR 公开端点失败已使 MCP-001 进入 `TEST_FAILED`，回归通过不能替代核心 OAuth 成功路径。

## 交接建议

交回功能实现 Agent，优先修复或明确公开 DCR 注册端点，使标准公共客户端注册至少返回 `200/201 application/json` 和 `client_id`，且不泄露内部异常。修复后保持测试目录只读，由测试 Agent 使用本报告中的同一隔离命令独立复测。

若项目决定 DCR 仅作为非必需兼容能力并不修复，则应由项目管理 Agent 更新任务范围/验收口径；测试 Agent 不自行放宽成功路径门禁。

## 黑盒声明

本阶段只通过公开 HTTP/JSON/JSON-RPC 输入输出和公开数据库可观察结果编写/运行测试；未读取或分析生产实现代码，未修改生产代码或运行时依赖。

