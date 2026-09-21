# AUTH-002 RED

- 测试角色：测试 Agent
- 状态：RED_CONFIRMED
- 工作区：G:\job
- 环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres
- 依赖同步：uv sync --frozen --group test，成功

## 测试命令与结果

新增黑盒测试文件：backend/tests/test_auth_002.py

命令：

uv run --no-sync pytest tests/test_auth_002.py --tb=no -q

连续执行两次，结果均为：

7 failed in 4.02s
7 failed in 3.84s

失败测试覆盖：

- 合法登录签发 access/refresh、用户安全字段和过期配置。
- access token 访问当前用户接口。
- 未认证访问 /api/v1/auth/me/ 及 refresh token 冒充 access token。
- 错误密码和不存在用户统一错误。
- 缺失用户名或密码字段错误。

一个最小黑盒断言的实际摘要：

- 请求：POST /api/v1/auth/login/，不存在用户名和密码。
- 期望：401 INVALID_CREDENTIALS。
- 实际：404，text/html Not Found。

## 环境与前置排除

- uv 冻结依赖同步成功。
- 同一 PostgreSQL pytest 隔离数据库中，AUTH-001、健康和 URL 回归命令结果为 9 passed。
- AUTH-002 测试正常收集并执行，无夹具导入、数据库连接或测试数据库创建错误。
- 失败稳定复现，原因是登录公开行为尚未提供/未满足契约，不是测试环境阻塞。

## 期望行为

- 正确凭据返回 200、可验证的 access/refresh token、access_expires_in=1800、refresh_expires_in=604800 和安全 user。
- access token 类型和 refresh token 类型正确，token 有效期与契约一致。
- access token 可访问 /api/v1/auth/me/，只返回当前用户 id、username、email。
- refresh token 不得直接访问 /me/；未认证访问 /me/ 返回 401。
- 错误密码、不存在用户统一返回 401 INVALID_CREDENTIALS。
- 缺失字段返回 400 VALIDATION_ERROR 和 details。

## 实际行为

登录端点对不存在用户的公开请求返回 404 Not Found，未达到 AUTH-002 登录契约；因此依赖登录的 token、/me/、过期配置和错误结构断言均失败。

## 覆盖的验收标准

- 登录 token 签发和有效期。
- 当前用户认证与安全响应。
- 未认证及错误 token 拒绝。
- 错误凭据统一 4xx。
- 缺失字段结构化 4xx。

## 未覆盖风险

- 登录实现完成后需重复运行同一 AUTH-002 测试集。
- Refresh token 轮换、退出黑名单和前端刷新队列属于后续范围，未在 AUTH-002 验收。

- 黑盒声明：仅依据公开 HTTP API、pytest 隔离数据库、任务契约和相邻回归结果完成验证；未读取或分析 backend/apps、backend/config 或 frontend/src 生产实现代码。