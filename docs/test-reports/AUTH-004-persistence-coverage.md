# AUTH-004 Blacklist Persistence Coverage

- 测试角色：测试 Agent
- 状态：COVERAGE_CONFIRMED
- 工作区：G:\job
- 环境：PostgreSQL 17.11；uv 0.7.21；Python 3.11.13
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres

## 新增覆盖

测试：backend/tests/test_auth_004.py::test_logout_blacklist_persists_across_a_new_django_process

命令：

uv run --no-sync pytest tests/test_auth_004.py::test_logout_blacklist_persists_across_a_new_django_process --tb=no -q

结果：1 passed in 4.93s

测试先以事务提交 logout blacklist，再启动独立 uv/Django shell 进程，连接同一 pytest PostgreSQL 测试数据库并调用公开 refresh API；独立进程返回 401 INVALID_REFRESH_TOKEN，证明 blacklist 不依赖当前 Django 进程内存。

## RED/覆盖依据

本补充测试在当前实现上直接通过，因此没有新的 RED_CONFIRMED 失败证据；它补齐了 AUTH-004 验收要求的“服务/进程重启后 blacklist 持久有效”覆盖。完整 AUTH-004 回归仍需继续执行。

- 黑盒声明：仅通过公开 logout/refresh API 和独立 Django 进程验证，未读取或分析生产实现代码。