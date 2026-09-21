# SEC-001 RED 测试报告

## 状态

RED_CONFIRMED

## 测试角色与黑盒边界

- 测试角色：测试 Agent
- 新增测试：`backend/tests/test_sec_001.py`
- 观察范围仅为公开 `manage.py check --deploy`、HTTP 响应和日志输出
- 未读取或分析 `backend/apps/`、`backend/config/` 生产源码

## 环境与命令

- 工作目录：`G:\job\backend`
- PostgreSQL：使用 `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test`，成功
- 测试命令：

  ```text
  uv run --no-sync pytest tests/test_sec_001.py --tb=no -q
  ```

## 结果

```text
1 failed, 5 passed in 8.98s
Exit code: 1
```

## RED 失败证据

公开部署检查在以下环境下运行：

```text
DJANGO_SECRET_KEY=insecure-test-only-key
DJANGO_DEBUG=true
CORS_ALLOWED_ORIGINS=*
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres
uv run --no-sync python manage.py check --deploy --fail-level WARNING
```

该命令确实发现安全警告并失败，但公开输出只包含 clickjacking、HSTS、HTTPS 重定向、弱密钥和安全 Cookie 等其他项目，未指出 `DEBUG=true` 或通配 CORS 风险。专项测试因此失败，证据是生产安全检查未对任务契约要求的 DEBUG/CORS 配置提供可观察拒绝或诊断行为。这是安全门禁缺口，不是依赖、数据库、语法或测试夹具错误。

## 已通过的黑盒检查

- 缺少敏感配置时公开部署检查拒绝启动/检查；
- 健康响应的 `X-Content-Type-Options`、`Referrer-Policy` 和非通配 CORS 行为；
- 注册与未认证错误响应不回显密码、Token、Authorization、SQL 或堆栈；
- 认证请求日志可观察且不包含凭据或 Authorization；
- 登录重复请求保持安全 4xx，未出现 5xx；本轮未观察到稳定 429 限流响应，公开限流入口尚未得到行为证据。

## 覆盖范围

测试覆盖缺少敏感配置危险默认、生产 DEBUG/CORS 安全检查、HTTP 安全头、错误响应脱敏、日志脱敏及登录限流入口探测。

## 结论

确认 `RED_CONFIRMED`，将 DEBUG/CORS 生产安全检查缺口回流实现阶段。未修改生产实现目录。
