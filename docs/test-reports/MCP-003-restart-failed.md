# MCP-003 Real Restart / Multi-Process TEST_FAILED

- 状态：`TEST_FAILED`
- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 环境：Windows；隔离 PostgreSQL 17.11（端口 55439）；uv 0.7.21；Python 3.11.13
- 测试文件：`backend/tests/test_mcp_003_real_restart.py`
- 允许修改：仅测试目录和测试报告；未读取或修改生产实现

## 测试目标

通过真实 HTTP 和独立 uvicorn 进程证明：

1. 服务 A 创建投递并生成 proposal。
2. 停止 A，启动全新的服务 B，使用同一 Bearer Token apply。
3. 启动并行服务 C，通过不同端口重放 apply/read，验证多进程等价。

测试没有导入 Django、MCP、模型、URL 或生产模块，只使用 `requests`、OAuth HTTP、`/mcp` JSON-RPC 和进程生命周期。

## 命令与环境准备

隔离数据库迁移检查：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -MigrateOnly -Port 55439 -DatabaseName app009_test
```

结果：

```text
No migrations to apply.
```

真实 HTTP 测试：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 `
  -PytestArguments @('tests/test_mcp_003_real_restart.py','--tb=no','-q','-s') `
  -Port 55439 -DatabaseName app009_test
```

结果：

```text
1 failed, 0 passed, 0 errors
```

## 实际生命周期与公开响应

### 服务 A

- 启动方式：`uv run --no-sync python -m uvicorn backend.config.asgi:application --host 127.0.0.1 --port <动态端口>`
- 实际监听端口：`53564`
- 启动成功，HTTP `GET /mcp` 未认证请求返回 `401`。
- 公开注册：`POST /api/v1/auth/register/` 返回 `201`。
- OAuth 登录：`GET/POST /oauth/login` 成功建立 session。
- DCR：`POST /oauth/register` 返回 `201`。
- Authorization Code + PKCE S256：授权和 token 交换成功，取得包含 `applications:write` 的 Bearer Token。
- 首次公开业务请求：`POST /mcp` 调用 `create_application` 返回 HTTP `500 Internal Server Error`。

服务日志中可观察到的异常摘要：

```text
RuntimeError: Task group is not initialized. Make sure to use run().
```

异常发生在真实 ASGI/Streamable HTTP 请求处理阶段；不是 OAuth fixture、数据库迁移、端口绑定或测试数据创建失败。

### 服务 A 清理

测试的 `finally` 路径停止了服务 A 并关闭日志文件。第一次测试尝试曾发现固定端口残留进程，已将测试改为动态空闲端口并补充启动失败清理；后续失败使用动态端口，未再出现端口冲突。

### 服务 B/C

由于服务 A 在 preview 前的首次 `create_application` 已返回 500，无法获得合法业务目标和 proposal，测试按安全边界没有启动或声称验证服务 B/C。故不能推断 proposal 在重启或多副本下可用。

## 结论

本次真实 HTTP 黑盒验证未通过，阻塞点是实际 uvicorn/ASGI 进程中的 MCP Streamable HTTP 生命周期初始化，而不是 PostgreSQL 或 OAuth 环境问题。当前没有真实服务 A→B 的 proposal 重启证据，也没有 A/B/C 多副本路由证据。

需要功能实现 Agent 在不修改测试的前提下修复/提供正式的 ASGI lifespan 启动方式，使实际 uvicorn 请求能进入 MCP 工具处理；修复后必须重新运行同一测试命令，并由测试 Agent独立确认：

- A 的 preview 返回 `proposal_id`；
- A 停止、B 启动后 apply 成功且 `proposal_id`、`audit_id`、业务结果一致；
- C 并行重放返回原 `audit_id` 和 `idempotent_replay=true`；
- 所有进程最终清理，未留下监听端口。

## 黑盒声明

本报告只记录真实 HTTP、OAuth、MCP 响应、进程生命周期和运行日志摘要；未读取或分析 `backend/apps/`、`backend/config/` 源码，未直接读表，未修改生产代码、依赖、任务单或验收记录。
