# AUTH-003 Refresh Token 轮换与 7 天登录态

- 状态：`DONE`
- 用户价值：Access Token 过期时可安全换取新凭据，登录态最长维持 7 天。
- 范围：`POST /api/v1/auth/refresh/`、Refresh Token 7 天绝对有效期、rotation、旧 Token 黑名单。
- 非范围：退出接口、前端 Axios 队列、Cookie 方案、第三方登录。
- 依赖：`AUTH-002`。
- 允许修改范围：测试 Agent：`backend/tests/`、`docs/test-reports/`；实现 Agent：`backend/apps/`、`backend/config/`、运行时依赖、`docs/implementation-notes/`；项目管理 Agent：仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`。

## 业务规则与公开契约

- `POST /api/v1/auth/refresh/` 接受当前 `refresh`，成功返回 `200`、新的 `access`、轮换后的 `refresh`、1800 和 604800 秒有效期。
- Refresh Token 的绝对有效期为 7 天，不因刷新而延长超过原登录态截止时间；客户端可据此维护 `expiresAt`。
- 每次成功刷新立即使旧 Refresh Token 无效并进入黑名单。
- 过期、伪造、已轮换或已黑名单 Token 返回 `401 INVALID_REFRESH_TOKEN`。

## 验收标准

- [x] 有效 Refresh Token 可换取新 Token，新的 Access Token 可访问 `/me/`。
- [x] 轮换后旧 Refresh Token 再次刷新失败。
- [x] 7 天截止后刷新失败，不会因反复刷新无限延长。
- [x] 刷新错误结构稳定且不泄露 Token 内容。
- [x] 测试覆盖重复使用边界或明确记录其实现约束，并先取得 RED。

## 风险与测试边界

- 黑名单存储必须持久化到项目指定数据库；不以进程内字典替代。
- 本任务不负责前端如何排队重试，前端任务只消费此公开契约。
