# AUTH-002 验收记录

- 状态：`DONE`
- 验收角色：项目管理 Agent
- 验收日期：2026-09-20
- 任务单：`docs/tasks/AUTH-002.md`
- RED 报告：`docs/test-reports/AUTH-002-red.md`
- 测试通过报告：`docs/test-reports/AUTH-002-passed.md`
- 实现说明：`docs/implementation-notes/AUTH-002.md`
- 验收环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13；`DATABASE_URL=postgresql://postgres:<password>@127.0.0.1:5432/postgres`（凭据脱敏）

## 系统设计登录契约对照

- 登录接受用户名和密码；正确凭据返回 `200`，响应包含 access、refresh、`access_expires_in=1800`、`refresh_expires_in=604800` 和安全 user 字段。
- `GET /api/v1/auth/me/` 使用 `Authorization: Bearer <access_token>`，成功只返回当前用户 `id`、`username`、`email`。
- 用户名不存在、密码错误和禁用用户统一返回 `401 INVALID_CREDENTIALS`，不得泄露用户是否存在。
- Access Token 有效期为 30 分钟，Refresh Token 有效期为 7 天；刷新轮换、退出黑名单和前端 Token 存储属于后续任务，不在本次范围。

## 标准与证据

- [x] 标准 1：正确凭据签发可验证的 Access/Refresh Token，过期秒数准确。独立通过报告确认登录返回 `200`、两个 JWT，`access_expires_in` 为 `1800`，`refresh_expires_in` 为 `604800`；JWT 类型和生命周期均正确。
- [x] 标准 2：正确 Access Token 可访问 `/me/` 并只返回当前用户安全字段。独立通过报告确认 Bearer access token 可访问 `GET /api/v1/auth/me/`，响应仅包含 `id`、`username`、`email`。
- [x] 标准 3：错误凭据统一为 `401 INVALID_CREDENTIALS`。独立通过报告确认错误密码和不存在用户均返回统一错误码；实现说明同时覆盖禁用用户统一处理。
- [x] 标准 4：未认证 `/me/` 为 401，不能通过请求体伪造用户身份。独立通过报告确认未认证访问 `/me/` 返回 `401`，refresh token 不能作为 access token 访问 `/me/`；登录与当前用户响应不包含密码、哈希或额外敏感字段。
- [x] 标准 5：测试先确认签发和 `/me/` 缺失，再独立复测通过。RED 报告记录同一 AUTH-002 测试集连续两次 `7 failed`，失败由登录端点缺失导致；实现说明状态为 `READY_FOR_TEST`；测试 Agent 独立联合复测为 `21 passed`。

## 回归与质量门禁

- [x] `uv sync --frozen --group test` 成功。
- [x] AUTH-001、DB-001、健康和 URL 回归均通过；联合测试总计 `21 passed`。
- [x] `manage.py check` 退出码 0，无系统检查问题。
- [x] `makemigrations --check --dry-run` 退出码 0，`No changes detected`。
- [x] `migrate --plan` 退出码 0，迁移计划可生成。
- [x] `manage.py test --noinput --verbosity 0` 退出码 0。
- [x] 任务单、RED 报告、实现说明、独立通过报告和本验收记录齐全；本次仅修改 `docs/acceptance/` 和 `docs/tasks/`。

## 结论

AUTH-002 的登录签发、错误响应、当前用户认证边界、JWT 生命周期、安全字段和回归门禁均满足任务单及系统设计契约。项目管理验收通过，任务状态设置为 `DONE`。
