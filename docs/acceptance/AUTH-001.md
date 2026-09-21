# AUTH-001 验收记录

- 状态：`DONE`
- 验收角色：项目管理 Agent
- 验收日期：2026-09-20
- 任务单：`docs/tasks/AUTH-001.md`
- RED 报告：`docs/test-reports/AUTH-001-red.md`
- 测试通过报告：`docs/test-reports/AUTH-001-passed.md`
- 实现说明：`docs/implementation-notes/AUTH-001.md`
- 验收环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13；`DATABASE_URL=postgresql://postgres:<password>@127.0.0.1:5432/postgres`（凭据脱敏）

## 系统设计注册契约对照

- 用户名必填，长度 3～30；邮箱可选但必须符合格式；密码至少 8 位并通过 Django 密码校验器；确认密码必须一致。
- 注册使用 `create_user()` 写入 PostgreSQL，成功后不自动登录，仅返回安全用户字段。
- 重复用户名返回 `409 USERNAME_ALREADY_EXISTS`；密码不一致返回 `400 PASSWORDS_DO_NOT_MATCH`；弱密码返回 `400 WEAK_PASSWORD`；字段错误返回 `400 VALIDATION_ERROR` 并携带 `details`。
- 注册成功后用户实际存在于 PostgreSQL，数据库不保存明文密码，响应不返回密码或密码哈希。

## 标准与证据

- [x] 标准 1：合法注册返回 201，用户持久化且重新查询后仍存在。`AUTH-001-passed.md` 记录匿名注册成功返回 201，合法用户已持久化到数据库。
- [x] 标准 2：密码为 Django 哈希，不能以明文保存；正确密码可校验。独立通过报告确认 `check_password()` 成功，数据库密码不是明文。
- [x] 标准 3：重复用户名、弱密码、密码不一致和字段格式错误符合契约。独立通过报告确认分别返回 `409 USERNAME_ALREADY_EXISTS`、`400 WEAK_PASSWORD`、`400 PASSWORDS_DO_NOT_MATCH` 和 `400 VALIDATION_ERROR`；非法用户名/邮箱错误位于 `details`。
- [x] 标准 4：响应不泄露密码、哈希或超出契约的敏感字段。独立通过报告确认成功响应仅包含 `id`、`username`、`email`、`date_joined`，不包含原始密码或密码哈希；注册允许匿名访问且不自动登录。
- [x] 标准 5：测试覆盖成功、边界、异常并先形成 `RED_CONFIRMED`。RED 报告记录注册端点缺失时同一测试集连续两次 `7 failed`；实现说明状态为 `READY_FOR_TEST`；测试 Agent 独立复测指定测试 `9 passed`，DB-001 回归 `5 passed`。

## 回归与质量门禁

- [x] `uv sync --frozen --group test` 成功。
- [x] `manage.py check` 退出码 0，无系统检查问题。
- [x] `makemigrations --check --dry-run` 退出码 0，`No changes detected`。
- [x] `migrate --plan` 退出码 0，迁移计划可生成。
- [x] `manage.py test --noinput --verbosity 0` 退出码 0。
- [x] PostgreSQL、测试数据库隔离、依赖锁定和健康/URL 回归均通过；DB-001 回归为 `5 passed`。
- [x] 任务单、RED 报告、实现说明、独立通过报告和本验收记录齐全；本次仅修改 `docs/acceptance/` 和 `docs/tasks/`。

## 结论

AUTH-001 的注册持久化、匿名访问、密码安全、输入错误校验、响应脱敏和 TDD 独立复测均满足任务单及系统设计契约。项目管理验收通过，任务状态设置为 `DONE`。
