# MCP-001 RED

- 状态：`RED_CONFIRMED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；PostgreSQL 17.11（隔离端口 55439）；uv 0.7.21；Python 3.11.13
- 依赖同步：`uv sync --frozen --group test`，成功；未修改依赖声明或锁文件
- 测试文件：`backend/tests/test_mcp_001.py`
- 生产实现：未读取、未修改 `backend/apps/`、`backend/config/`；未修改其他生产代码

## 命令与结果

语法检查：

```text
uv run python -m py_compile tests/test_mcp_001.py
通过
```

隔离 PostgreSQL 定向测试（连续两次相同结果）：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_001.py','--tb=no','-q') `
  -Port 55439 -DatabaseName app009_test
```

两次结果均为：

```text
9 failed, 5 passed, 7 skipped
```

通过项为非法 PKCE/授权请求拒绝；失败项集中在当前缺失的 MCP/OAuth 公开端点和认证行为。失败不是语法错误、数据库连接错误、夹具错误或测试配置错误。

## 覆盖的公开行为

新增黑盒测试覆盖：

- Protected Resource Metadata：`/.well-known/oauth-protected-resource/mcp` 的资源 URI、授权服务器、scope、Bearer header 声明。
- Authorization Server Metadata：issuer、authorization/token endpoint、Authorization Code、PKCE `S256`、`applications:read`、CIMD 支持声明。
- 未认证/无效/错误 scheme 的 `/mcp` 请求：应为 `401`、带 `WWW-Authenticate` 和 `resource_metadata`，且不得执行 JSON-RPC。
- 现有网页 JWT 不得被当作 MCP Resource Token 接受。
- Authorization Code + PKCE 的缺失 PKCE、`plain`、redirect URI、resource、超范围 scope 拒绝。
- token endpoint 对未知 authorization code 和错误 resource 的拒绝。
- 现代 `server/discover`、`tools/list`、`tools/call` 无 `initialize` 前置要求。
- `tools/list` 白名单只包含 `find_applications`，并公开只读标记、筛选/分页 schema，拒绝 `user_id`。
- `find_applications` 的 APP-012 公司聚合结构、`content` 与 `structuredContent`、空结果和只读约束。
- 两个 OAuth 用户的投递隔离、跨用户 application ID 查询返回空结果。
- 未声明或未知工具/方法的 JSON-RPC 错误。
- 受众不匹配 Token 和缺少 `applications:read` scope 的用例已准备为黑盒联调测试。

成功工具调用、受众错误 Token、缺 scope Token 和跨用户数据用例需要外部 OAuth 联调环境提供以下变量，不使用内部 token 生成或模型访问绕过黑盒边界：

```text
MCP_TEST_ACCESS_TOKEN_A
MCP_TEST_ACCESS_TOKEN_B
MCP_TEST_ACCESS_TOKEN_WRONG_AUDIENCE
MCP_TEST_ACCESS_TOKEN_NO_READ
MCP_TEST_FOREIGN_APPLICATION_ID
```

本地未提供这些凭据，因此 7 项为显式跳过，不把环境缺失误报为功能失败；实现交付后应在真实 CIMD/PKCE 客户端环境补跑。

## RED 证据

当前实现对以下强制公开行为尚未提供可观察成功/认证入口：

1. 两个发现文档端点不可满足契约。
2. `/mcp` 未认证请求无法返回 MCP 要求的 `401` 与资源发现挑战。
3. 无效 Bearer/错误 scheme 和网页 JWT 的 MCP 资源认证边界未建立。
4. token endpoint 未能按 OAuth 错误契约处理未知 code/resource。

同一隔离数据库、同一命令连续运行两次均产生 `9 failed, 5 passed, 7 skipped`，失败位置稳定，符合“需求行为缺失导致 RED”的门禁要求。5 个授权参数拒绝测试已通过，证明测试请求格式和基础 Django/数据库夹具可用。

## 实现交接建议

请交由功能实现 Agent，按 MCP-001 任务单先实现：

1. Protected Resource Metadata 和 Authorization Server Metadata；
2. CIMD 优先的 Authorization Code + PKCE `S256`、`resource`/受众和标准错误；
3. stateless Streamable HTTP `/mcp` 与 `server/discover`；
4. Bearer scope 校验和 `tools/list` 白名单；
5. APP-012 聚合查询的 `find_applications` 及当前用户隔离。

实现完成后状态进入 `READY_FOR_TEST`，由测试 Agent 使用同一测试文件、同一命令和外部 OAuth 联调变量独立复测；测试目录视为只读。

## 黑盒声明

本阶段仅通过公开 HTTP/JSON/JSON-RPC 输入输出编写和运行测试；未读取或分析生产实现代码，未修改生产实现、运行时依赖、测试门槛或共享配置。

