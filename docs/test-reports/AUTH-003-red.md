# AUTH-003 RED

- 测试角色：测试 Agent
- 状态：RED_CONFIRMED
- 工作区：G:\job
- 环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres
- 依赖同步：uv sync --frozen --group test，成功

## 测试命令与结果

新增黑盒测试文件：backend/tests/test_auth_003.py

命令：

uv run --no-sync pytest tests/test_auth_003.py --tb=no -q

连续执行两次，结果均为：

7 failed in 6.94s
7 failed in 6.93s

一个最小黑盒断言的实际摘要：

- 请求：使用 AUTH-002 已签发的有效 refresh token 调用 POST /api/v1/auth/refresh/。
- 期望：200，返回轮换后的 access/refresh。
- 实际：404 Not Found。

## 覆盖行为

- 有效 refresh token 换取新 token。
- 新 access token 访问 /me/。
- refresh token 轮换后旧 token 重放失败。
- 原始 7 天绝对截止时间不被刷新延长。
- 伪造、空值、过期、access token 冒充 refresh token 返回 401 INVALID_REFRESH_TOKEN。
- 错误响应不回显敏感 token。

## 环境与稳定性

- uv 冻结依赖同步成功。
- 测试正常收集并执行，未发生夹具导入或数据库连接错误。
- AUTH-002 前置登录行为已在此前独立复测通过；本轮失败集中于 refresh 行为缺失。
- 失败连续复现，属于 AUTH-003 公开端点/行为未满足契约，不是环境阻塞。

## 覆盖的验收标准

- 有效 Refresh Token 轮换并获得可访问 /me/ 的新 Access Token。
- 旧 Refresh Token 轮换后不可重放。
- Refresh Token 绝对 7 天有效期不因轮换无限延长。
- 过期、伪造、已轮换和错误类型 Token 的 401 错误结构及脱敏。

## 未覆盖风险

- 实现完成后需由测试 Agent 使用同一测试集独立复测。
- AUTH-003 不覆盖退出接口、前端刷新队列和 Cookie 方案。

- 黑盒声明：仅依据公开 HTTP API、公开 token 类型/生命周期、pytest 隔离数据库和任务契约完成验证；未读取或分析 backend/apps、backend/config 或 frontend/src 生产实现代码。