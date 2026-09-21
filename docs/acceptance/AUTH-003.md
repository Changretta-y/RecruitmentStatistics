# AUTH-003 验收记录

- 状态：`DONE`
- 验收角色：项目管理 Agent
- 验收日期：2026-09-20
- 任务单：`docs/tasks/AUTH-003.md`
- RED 报告：`docs/test-reports/AUTH-003-red.md`
- 测试通过报告：`docs/test-reports/AUTH-003-passed.md`
- 实现说明：`docs/implementation-notes/AUTH-003.md`
- 验收环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13；`DATABASE_URL=postgresql://postgres:<password>@127.0.0.1:5432/postgres`（凭据脱敏）

## 系统设计刷新契约对照

- `POST /api/v1/auth/refresh/` 接受当前 refresh token，成功返回新的 access、轮换后的 refresh、`access_expires_in=1800` 和 `refresh_expires_in=604800`。
- Refresh Token 有效期为 7 天，启用 rotation；每次刷新后旧 Token 立即进入持久化黑名单并失效。
- 刷新不得把登录态延长超过原始 7 天截止时间；错误响应不得泄露 Token 内容。

## 标准与证据

- [x] 标准 1：有效 Refresh Token 可换取新 Token，新的 Access Token 可访问 `/me/`。独立通过报告确认有效 refresh token 轮换成功，返回新的 access/refresh 和 1800/604800 秒配置；新 access token 可访问 `/api/v1/auth/me/`。
- [x] 标准 2：轮换后旧 Refresh Token 再次刷新失败。独立通过报告确认旧 refresh token 重放返回 `401 INVALID_REFRESH_TOKEN`，且旧 Token 已写入持久化 token_blacklist 数据库。
- [x] 标准 3：7 天截止后刷新失败，不会因反复刷新无限延长。独立通过报告确认轮换后的 refresh token 未超过原始 7 天绝对截止时间；实现说明记录新 Token 保留旧 Token 原始 `exp`。
- [x] 标准 4：刷新错误结构稳定且不泄露 Token 内容。独立通过报告确认伪造、空值、过期、已黑名单和 access token 冒充 refresh token 均返回 `401 INVALID_REFRESH_TOKEN`，错误响应不回显敏感 Token；成功响应仅包含 access、refresh 和生命周期字段。
- [x] 标准 5：测试覆盖重复使用边界或明确记录实现约束，并先取得 RED。RED 报告记录同一测试集连续两次 `7 failed`，失败集中于 refresh 行为缺失；实现说明状态为 `READY_FOR_TEST`；测试 Agent 独立联合复测为 `28 passed`，覆盖旧 Token 重放边界。

## 回归与质量门禁

- [x] `uv sync --frozen --group test` 成功。
- [x] AUTH-001、AUTH-002、DB-001、健康和 URL 回归全部通过；联合测试总计 `28 passed`。
- [x] PostgreSQL 后端、测试数据库隔离、依赖锁定和 token_blacklist 持久化基线均通过。
- [x] 任务单、RED 报告、实现说明、独立通过报告和本验收记录齐全；本次仅修改 `docs/acceptance/` 和 `docs/tasks/`。

## 结论

AUTH-003 的 Refresh Token 轮换、旧 Token 失效、7 天绝对过期、无效 Token 拒绝、错误响应脱敏、黑名单持久化和全量回归均满足任务单及系统设计契约。项目管理验收通过，任务状态设置为 `DONE`。
