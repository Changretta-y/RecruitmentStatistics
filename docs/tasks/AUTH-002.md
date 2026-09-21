# AUTH-002 登录签发与当前用户

- 状态：`DONE`
- 用户价值：已注册用户可登录并访问自己的当前用户信息。
- 范围：`POST /api/v1/auth/login/`、`GET /api/v1/auth/me/`、密码认证、Access/Refresh Token 初次签发。
- 非范围：刷新轮换、退出黑名单、前端 Token 存储、登录限流。
- 依赖：`AUTH-001`。
- 允许修改范围：测试 Agent：`backend/tests/`、`docs/test-reports/`；实现 Agent：`backend/apps/`、`backend/config/`、运行时依赖、`docs/implementation-notes/`；项目管理 Agent：仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`。

## 业务规则与公开契约

- `POST /api/v1/auth/login/` 接受 `username`、`password`；正确凭据返回 `200`。
- 成功响应包含 `access`、`refresh`、`access_expires_in=1800`、`refresh_expires_in=604800` 和安全字段 `user`。
- `GET /api/v1/auth/me/` 需要 `Authorization: Bearer <access>`，返回当前用户 `id`、`username`、`email`。
- 用户名不存在、密码错误、禁用用户统一返回 `401 INVALID_CREDENTIALS`。

## 输入、输出与错误行为

- 缺少/格式错误字段返回 `400 VALIDATION_ERROR`。
- 未认证访问 `/me/` 返回 `401`；无效或过期 Access Token 不得返回用户数据。
- 登录响应不泄露密码、哈希、用户是否存在的额外信息，也不记录完整 Token。

## 验收标准

- [x] 正确凭据签发可验证的 Access/Refresh Token，过期秒数准确。
- [x] 正确 Access Token 可访问 `/me/` 并只返回当前用户安全字段。
- [x] 错误凭据统一为 `401 INVALID_CREDENTIALS`。
- [x] 未认证 `/me/` 为 401，不能通过请求体伪造用户身份。
- [x] 测试先确认签发和 `/me/` 缺失，再独立复测通过。

## 风险与测试边界

- Token 具体 JWT claims 可由实现选择，但有效期和后续轮换契约不可改变。
- 本任务不验收 7 天续期、黑名单和前端刷新队列。
