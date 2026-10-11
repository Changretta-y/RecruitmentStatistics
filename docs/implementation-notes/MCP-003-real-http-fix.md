# MCP-003 真实 HTTP 生命周期修复

## 状态

READY_FOR_TEST

## 根因

`MCPServer.streamable_http_app()` 返回的 Starlette 应用通过自己的 lifespan
上下文启动 `StreamableHTTPSessionManager`。该上下文负责初始化 Streamable HTTP
传输所使用的 task group。原来的 `backend.config.asgi.application` 只在 HTTP
请求到来时手动调用 MCP 应用，没有转发 Uvicorn 的 `lifespan.startup` 和
`lifespan.shutdown` 事件，因此真实 uvicorn 进程第一次 `tools/call` 会触发：

```text
RuntimeError: Task group is not initialized. Make sure to use run().
```

## 修复

- `backend/config/asgi.py` 现在把顶层 ASGI lifespan scope 转发给
  `mcp_asgi_app`，并显式设置其 `app` scope。
- MCP Starlette 应用因此会正常进入 `StreamableHTTPSessionManager.run()`，在
  Uvicorn 宣布 startup complete 前完成 task group 初始化，并在 shutdown 时
  释放资源。
- HTTP 路由仍保持现有行为：`/mcp` 和 protected-resource metadata 交给 MCP
  应用，其余路径交给 Django；未修改 OAuth Bearer 校验、per-tool
  `applications:write` scope、工具白名单或 `structuredContent` 契约。
- 为延迟导入 Django 的 ASGI 入口保留 Ruff 的显式 `E402` 豁免；没有新增依赖
  或数据库迁移。

## 验证

环境：Python 3.11.13、uv 0.7.21、隔离 PostgreSQL 17.11（端口 55439）。

通过：

```text
uv run python manage.py check
System check identified no issues (0 silenced).

uv run ruff check apps/mcp config/asgi.py
All checks passed!

run-isolated-postgres.ps1 -PytestArguments @(
  'tests/test_mcp_003_real_restart.py','--tb=no','-q','-s'
) -Port 55439 -DatabaseName app009_test
1 passed in 12.83s
```

真实黑盒测试已验证：服务 A 通过 OAuth Bearer 创建投递并预览，A 停止后服务
B 使用同一 token 应用 proposal，服务 C 并行重放并读取结果；proposal、audit
和 `idempotent_replay=true` 在进程边界后均保持一致。

裸跑 `makemigrations --check --dry-run` 在未设置项目数据库连接的 shell 中无法
连接数据库；本修复未修改模型或迁移。请测试 Agent 使用隔离 PostgreSQL 命令
执行迁移检查及独立复测。
