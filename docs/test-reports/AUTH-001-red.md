# AUTH-001 RED

- 测试角色：测试 Agent
- 状态：RED_CONFIRMED
- 环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13
- 工作区：G:\job
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres
- 依赖同步：uv sync --frozen --group test，成功

## 测试命令与结果

新增黑盒测试文件：backend/tests/test_auth_001.py

命令：

uv run --no-sync pytest tests/test_auth_001.py --tb=no -q

连续执行两次，结果均为：

7 failed in 1.79s
7 failed in 1.91s

失败测试：

- test_register_persists_user_with_hashed_password_and_safe_response
- test_register_is_available_without_authentication
- test_duplicate_username_returns_explicit_conflict_code
- test_password_mismatch_returns_explicit_error_code
- test_weak_password_returns_explicit_error_code
- test_invalid_registration_fields_return_structured_validation_error[overrides0-username]
- test_invalid_registration_fields_return_structured_validation_error[overrides1-email]

公开客户端探针：

- POST /api/v1/auth/register/ 使用合法注册数据
- 实际状态：404 Not Found，空请求体
- 命令退出码：0

相邻回归：

uv run --no-sync pytest tests/test_health.py tests/test_urls.py --tb=no -q

结果：2 passed in 0.10s

## 期望行为

- 合法未认证注册返回 201，并持久化用户。
- 密码以 Django 哈希保存，原始密码不明文存储。
- 响应只包含 id、username、email、date_joined，不包含密码或密码哈希。
- 重复用户名返回 409 USERNAME_ALREADY_EXISTS。
- 密码不一致返回 400 PASSWORDS_DO_NOT_MATCH。
- 弱密码返回 400 WEAK_PASSWORD。
- 用户名长度、邮箱格式等字段错误返回 400 VALIDATION_ERROR，并在 details 中返回字段错误。

## 实际行为

注册公开端点当前返回 404 Not Found，因此成功、未认证访问、重复用户名、密码校验和字段错误的全部公开行为测试均未达到契约。

## 是否稳定复现

是。同一测试集连续两次均为 7 failed；PostgreSQL 可用，依赖同步成功，相邻健康和 URL 测试通过，已排除测试收集、夹具和基础环境错误。

## 覆盖的验收标准

- 合法注册返回 201，用户持久化。
- 密码哈希保存且响应不泄露密码或哈希。
- 重复用户名、弱密码、密码不一致和字段格式错误返回契约规定的 4xx。
- 注册端点允许未认证访问。
- 成功响应不包含超出契约的敏感字段。

## 未覆盖风险

- 登录、JWT、Token 刷新、退出和邮箱验证属于 AUTH-002 及后续任务，未在本任务覆盖。
- 注册实现完成后需由测试 Agent 使用同一测试集独立复测。

- 黑盒声明：仅通过公开 HTTP API、公开 Django 用户持久化结果、测试客户端和相邻公开测试验证；未读取或分析 backend/apps、backend/config 或 frontend/src 生产实现代码。