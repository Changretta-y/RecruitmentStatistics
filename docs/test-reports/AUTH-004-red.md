# AUTH-004 RED

- 测试角色：测试 Agent
- 状态：RED_CONFIRMED
- 工作区：G:\job
- 环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres
- 依赖同步：uv sync --frozen --group test，成功

## 测试结果

新增测试：backend/tests/test_auth_004.py

命令：

uv run --no-sync pytest tests/test_auth_004.py --tb=no -q

连续两次结果：

- 4 failed, 4 passed in 9.71s
- 4 failed, 4 passed in 9.41s

最小黑盒断言：

- 有效 access + refresh 请求 POST /api/v1/auth/logout/
- 期望：204 No Content
- 实际：404 Not Found

失败覆盖正常退出、refresh 黑名单、重复退出幂等、过期 refresh 退出和退出后 access 边界。通过项覆盖错误/缺失凭据安全 4xx、缺失 refresh 字段和未认证 /me/ 401。

## 结论

AUTH-004 logout 公开行为缺失，失败稳定复现；uv、PostgreSQL、pytest 隔离数据库和 AUTH-002 登录前置均正常，不是环境阻塞。

- 黑盒声明：仅依据公开 HTTP API、测试数据库和任务契约验证；未读取或分析 backend/apps、backend/config 或 frontend/src 生产实现代码。