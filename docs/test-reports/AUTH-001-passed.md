# AUTH-001 TEST_PASSED

- 测试角色：测试 Agent
- 状态：TEST_PASSED
- 工作区：G:\job
- 环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres
- 依赖同步：uv sync --frozen --group test，成功

## 指定测试结果

命令：

uv run --no-sync pytest tests/test_auth_001.py tests/test_health.py tests/test_urls.py --tb=no -q

结果：

9 passed in 4.14s

AUTH-001 覆盖并通过：

- 匿名请求注册成功，返回 201。
- 合法用户持久化到数据库。
- 正确密码可校验，数据库密码不是明文。
- 响应只包含 id、username、email、date_joined。
- 响应不包含原始密码或密码哈希。
- 弱密码返回 400 WEAK_PASSWORD。
- 密码不一致返回 400 PASSWORDS_DO_NOT_MATCH。
- 重复用户名返回 409 USERNAME_ALREADY_EXISTS。
- 非法用户名/邮箱字段返回 400 VALIDATION_ERROR，并返回 details 字段错误。

健康与 URL 回归测试通过。

## 数据库与迁移回归

命令：

uv run --no-sync pytest tests/test_db_001.py --tb=no -q

结果：

5 passed in 8.98s

覆盖 PostgreSQL 后端、测试数据库隔离、依赖锁定和公开 Django 测试运行器基线。

公开管理命令：

- uv run --no-sync python manage.py check：退出码 0；无系统检查问题。
- uv run --no-sync python manage.py makemigrations --check --dry-run：退出码 0；No changes detected。
- uv run --no-sync python manage.py migrate --plan：退出码 0；迁移计划可生成。
- uv run --no-sync python manage.py test --noinput --verbosity 0：退出码 0；Ran 0 tests，OK。

## 结论

AUTH-001 注册持久化、密码安全、匿名访问、输入校验、错误结构和响应脱敏均通过独立黑盒复测。

- 本次未修改 backend/tests/。
- 未修改或读取生产实现目录。
- 黑盒声明：仅依据公开 API、公开数据库测试行为、任务契约和回归命令完成复测。