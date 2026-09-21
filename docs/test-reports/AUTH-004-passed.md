# AUTH-004 TEST_PASSED

- 测试角色：测试 Agent
- 状态：TEST_PASSED
- 工作区：G:\job
- 环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres
- 依赖同步：uv sync --frozen --group test，成功
- 生产实现：未修改

## 完整复测

命令：

uv run --no-sync pytest tests/test_auth_004.py tests/test_auth_003.py tests/test_auth_002.py tests/test_auth_001.py tests/test_db_001.py tests/test_health.py tests/test_urls.py --tb=no -q

结果：

38 passed in 34.17s

## AUTH-004 验证结果

- 有效 access + refresh logout 返回 204 No Content，响应为空。
- logout 后 refresh token blacklist，再次 refresh 返回 401 INVALID_REFRESH_TOKEN。
- 重复 logout、过期 refresh logout 均幂等且不泄露 token 状态。
- 缺失、伪造、错误类型和跨用户 token 组合返回安全 4xx。
- 未认证访问 /me/ 返回 401。
- logout 和错误响应不泄露 access、refresh、密码或哈希。
- logout 后 refresh blacklist 在独立 Django 进程中仍持久有效：
  - 测试使用 transaction=True 提交 blacklist。
  - 通过独立 uv run --no-sync python manage.py shell 进程连接同一 pytest PostgreSQL 测试数据库。
  - 独立进程调用公开 refresh API 返回 status=401 和 INVALID_REFRESH_TOKEN。
  - 独立进程持久化测试：1 passed in 4.93s。

## 回归结果

AUTH-003、AUTH-002、AUTH-001、DB-001、健康和 URL 回归全部通过。

- 黑盒声明：仅依据公开 API、独立 Django 进程和 pytest 隔离数据库完成验证；未读取或分析 backend/apps、backend/config 或 frontend/src 生产实现代码。