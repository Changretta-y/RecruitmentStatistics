# AUTH-001 注册持久化与密码校验

- 状态：`DONE`
- 用户价值：用户可安全创建账号，重启服务后账号仍存在且密码不以明文保存。
- 范围：`POST /api/v1/auth/register/`、Django User 持久化、用户名/邮箱/密码/确认密码校验和统一错误结构。
- 非范围：登录、Token、退出、邮箱验证、找回密码、限流和前端页面。
- 依赖：`DB-001`。
- 允许修改范围：测试 Agent：`backend/tests/`、`docs/test-reports/`；实现 Agent：`backend/apps/`、`backend/config/`、`backend/manage.py`、运行时依赖、`docs/implementation-notes/`；项目管理 Agent：仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`。

## 业务规则与公开契约

- `POST /api/v1/auth/register/` 接受 `username`、可选 `email`、`password`、`password_confirm`。
- 用户名去首尾空格后长度 3～30；邮箱填写时符合邮箱格式；密码至少 8 位并通过 Django 密码校验器。
- 成功返回 `201`，只返回 `id`、`username`、`email`、`date_joined`，不返回密码或密码哈希。
- 注册不自动登录；重复用户名返回 `409 USERNAME_ALREADY_EXISTS`。

## 输入、输出与错误行为

- 两次密码不一致：`400 PASSWORDS_DO_NOT_MATCH`。
- 弱密码：`400 WEAK_PASSWORD`。
- 字段格式错误：`400 VALIDATION_ERROR`，`details` 按字段返回错误数组。
- 成功后数据库用户存在，`check_password()` 成功，原始密码和哈希均不出现在响应或日志中。

## 验收标准

- [x] 合法注册返回 201，用户持久化且重启/重新查询后仍存在。
- [x] 密码为 Django 哈希，不能以明文保存；正确密码可校验。
- [x] 重复用户名、弱密码、密码不一致和字段格式错误均符合契约。
- [x] 响应不泄露密码、哈希或超出契约的敏感字段。
- [x] 测试覆盖成功、边界、异常并先形成 `RED_CONFIRMED`。

## 风险与测试边界

- 不根据错误差异暴露密码之外的敏感信息；登录错误统一由后续 `AUTH-002` 负责。
- 本任务不要求注册成功后返回 JWT。
