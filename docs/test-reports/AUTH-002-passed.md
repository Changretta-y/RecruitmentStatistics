# AUTH-002 TEST_PASSED

- 测试角色：测试 Agent
- 状态：TEST_PASSED
- 工作区：G:\job
- 环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres
- 依赖同步：uv sync --frozen --group test，成功
- 测试修改：本次未修改 backend/tests/；未修改生产实现

## 指定联合测试

命令：

uv run --no-sync pytest tests/test_auth_002.py tests/test_auth_001.py tests/test_db_001.py tests/test_health.py tests/test_urls.py --tb=no -q

结果：

21 passed in 17.77s

## AUTH-002 验证结果

- 合法用户名密码登录返回 200、access token、refresh token、安全 user 字段。
- access_expires_in 为 1800，refresh_expires_in 为 604800。
- JWT access token 类型和 refresh token 类型正确，生命周期与契约一致。
- 登录响应仅返回安全用户字段，不包含密码或密码哈希。
- 正确 access token 可访问 GET /api/v1/auth/me/，只返回当前用户 id、username、email。
- 未认证访问 /me/ 返回 401。
- refresh token 不能作为 access token 访问 /me/。
- 错误密码和不存在用户返回 401 INVALID_CREDENTIALS。
- 缺失用户名或密码字段返回 400 VALIDATION_ERROR，并返回 details。
- AUTH-001 注册、DB-001 数据库隔离、健康和 URL 回归全部通过。

## 公开管理命令

- uv run --no-sync python manage.py check：退出码 0；无系统检查问题。
- uv run --no-sync python manage.py makemigrations --check --dry-run：退出码 0；No changes detected。
- uv run --no-sync python manage.py migrate --plan：退出码 0；迁移计划可生成。
- uv run --no-sync python manage.py test --noinput --verbosity 0：退出码 0；Ran 0 tests，OK。

## 结论

AUTH-002 登录签发、错误响应、当前用户认证边界、JWT 生命周期和安全字段已通过独立黑盒复测。

- 黑盒声明：仅依据公开 API、pytest 隔离数据库、任务契约和公开管理命令完成复测；未读取或分析生产实现代码。