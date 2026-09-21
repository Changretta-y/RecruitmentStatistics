# AUTH-004 退出失效与认证边界

- 状态：`DONE`
- 用户价值：用户退出后旧 Refresh Token 不能恢复登录，受保护接口始终有统一认证边界。
- 范围：`POST /api/v1/auth/logout/`、Refresh Token 黑名单、幂等退出、受保护认证错误。
- 非范围：前端清理/跳转、登录限流、操作审计和多因素认证。
- 依赖：`AUTH-003`。
- 允许修改范围：测试 Agent：`backend/tests/`、`docs/test-reports/`；实现 Agent：`backend/apps/`、`backend/config/`、运行时依赖、`docs/implementation-notes/`；项目管理 Agent：仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`。

## 业务规则与公开契约

- `POST /api/v1/auth/logout/` 需要有效 Access Token，请求体为当前 `refresh`，成功返回 `204 No Content`。
- 后端将 Refresh Token 加入黑名单；之后该 Token 不能刷新。
- Token 已过期或已黑名单时退出请求保持幂等：不得重新建立登录态，也不得抛出未处理异常。
- 所有受保护业务接口无凭据返回 401；越权投递资源由投递任务统一返回 404。

## 验收标准

- [x] 正常退出后 Refresh Token 刷新失败。
- [x] 重复退出不会抛出未处理异常，也不会泄露 Token 状态。
- [x] 未认证访问受保护 `/me/` 和投递接口均为 401。
- [x] 黑名单数据持久化，服务重启后失效结论不丢失。
- [x] 测试先确认退出失效行为缺失，再由测试 Agent 独立复测。

## 风险与测试边界

- 前端无论退出请求网络结果如何都要清理本地状态，由 `WEB-AUTH-002` 负责。
- 不在本任务中引入跨用户数据测试；由 `APP-003` 负责。

## 项目管理复验

- 初次验收因缺少服务/进程重启后的黑名单证据而回退至 `TEST_WRITING`。
- 补充覆盖报告已证明独立 Django 进程中的 refresh 仍返回 `401 INVALID_REFRESH_TOKEN`，完整回归更新为 `38 passed`、`TEST_PASSED`。
- 项目管理复验结论：`ACCEPTED`；任务状态：`DONE`。
