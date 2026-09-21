# AUTH-003 TEST_PASSED

- 测试角色：测试 Agent
- 状态：TEST_PASSED
- 工作区：G:\job
- 环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres
- 依赖同步：uv sync --frozen --group test，成功
- 测试/生产修改：本次未修改测试或生产实现

## 指定联合测试

命令：

uv run --no-sync pytest tests/test_auth_003.py tests/test_auth_002.py tests/test_auth_001.py tests/test_db_001.py tests/test_health.py tests/test_urls.py --tb=no -q

结果：

28 passed in 21.80s

## AUTH-003 验证结果

- 有效 refresh token 成功轮换，返回新的 access/refresh 和 1800/604800 秒配置。
- 新 access token 可访问 /api/v1/auth/me/。
- 旧 refresh token 重放返回 401 INVALID_REFRESH_TOKEN。
- 轮换后的 refresh token 未超过原始 7 天绝对截止时间。
- 伪造 token、空 token、过期 token 和 access token 冒充 refresh token 均返回 401 INVALID_REFRESH_TOKEN。
- 错误响应不回显敏感 token。
- 成功响应只包含 access、refresh 和生命周期字段，不泄露用户密码或哈希。

## 回归结果

- AUTH-002 登录、JWT 类型/生命周期和当前用户认证边界：通过。
- AUTH-001 注册、持久化、密码哈希和输入错误：通过。
- DB-001 PostgreSQL 后端、测试数据库隔离、依赖和公开管理命令回归：通过。
- 健康 API 和 URL 回归：通过。

## 结论

AUTH-003 refresh token 轮换、旧 token 失效、7 天绝对过期、错误 token 拒绝和敏感字段保护均通过独立黑盒复测。

- 黑盒声明：仅依据公开 API、公开 token 行为、pytest 隔离数据库、任务契约和回归测试完成验证；未读取或分析 backend/apps、backend/config 或 frontend/src 生产实现代码。