# SEC-001 独立复测报告

## 状态

TEST_PASSED

## 环境

- 工作目录：`G:\job\backend`
- PostgreSQL：`127.0.0.1:5432`
- `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- uv 依赖：`uv sync --frozen --group test` 成功
- Node/nvm：本轮仅涉及后端 Python 安全黑盒测试，不需要前端 Node 环境
- 测试 secret：仅为测试进程提供长随机 `DJANGO_SECRET_KEY`/`SECRET_KEY`，未写入项目配置

## 执行命令与结果

依赖同步：

```text
uv sync --frozen --group test
Audited 17 packages in 0.03ms
```

专项最终命令：

```text
$env:DATABASE_URL = 'postgresql://postgres:postgres@127.0.0.1:5432/postgres'
$env:DJANGO_SECRET_KEY = 'sec001-test-only-key-0123456789-abcdefghijklmnopqrstuvwxyz'
$env:SECRET_KEY = $env:DJANGO_SECRET_KEY
uv run --no-sync pytest tests/test_sec_001.py --tb=no -q
```

结果：

```text
6 passed in 8.81s
Exit code: 0
```

有限关联回归：

```text
uv run --no-sync pytest tests/test_auth_004.py tests/test_app_007.py tests/test_health.py tests/test_urls.py --tb=no -q
```

结果：

```text
16 passed in 19.32s
Exit code 0
```

## 覆盖证据

- 缺少敏感配置时公开部署检查拒绝危险默认；
- `DEBUG`/通配 CORS 的 deploy check 行为；
- HTTP 安全响应头与非通配 CORS；
- 错误响应不泄露堆栈、SQL、密码、Token 或 Authorization；
- 请求日志可观察且认证头/凭据脱敏；
- 登录限流入口保持安全 4xx，不产生 5xx；若存在 429 则保持稳定行为；
- AUTH-004、APP-007、health、URL 关联回归未受影响。

## 环境说明

首次直接执行专项时，正常 HTTP 用例进程未提供 secret，导致 4 项在 Django 请求初始化阶段因 `SECRET_KEY` 为空失败；该结果判定为测试环境缺少运行时配置，不作为安全行为失败。按项目环境规范为测试进程提供非生产长 secret 后，专项稳定通过 6/6。

未执行后端全量测试，避免超出本次关联复测范围；不得将其表述为全量通过。

## 结论

SEC-001 安全黑盒专项与必要关联回归通过，状态为 `TEST_PASSED`。本轮未修改生产实现目录。
