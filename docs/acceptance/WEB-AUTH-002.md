# WEB-AUTH-002 验收记录

- 状态：`DONE`
- 验收结论：`ACCEPTED`
- 验收角色：项目管理 Agent
- 验收日期：2026-09-21
- 任务单：`docs/tasks/WEB-AUTH-002.md`
- RED 报告：`docs/test-reports/WEB-AUTH-002-red.md`
- 测试通过报告：`docs/test-reports/WEB-AUTH-002-passed.md`
- 实现说明：`docs/implementation-notes/WEB-AUTH-002.md`
- 验收环境：`.nvmrc 20.19.0`；Node.js `v20.19.0`；npm `10.8.2`；Vitest `4.1.11`；Pinia `4.0.3`；Vue Router `5.3.1`

## 系统设计契约对照

- Pinia auth store 暴露 `user`、`initialized`、`loading`，Token 继续由统一存储管理，不复制到 Pinia 持久化状态。
- 应用启动读取统一 Token 存储；7 天期限过期立即清理，否则调用 `/api/v1/auth/me/`，必要时由 HTTP 层执行刷新。
- 未认证访问 `requiresAuth` 路由跳转 `/login?redirect=<原地址>`；已认证访问 `/login` 或 `/register` 跳转 `/applications`。
- logout 无论接口成功、HTTP 失败或网络错误都清理 Token 与 user，并导航登录页；初始化完成前保持加载态，避免未授权闪烁。

## 标准与证据

- [x] 标准 1：登录态初始化成功后 user 可用；无 Token、7 天过期或 `/me/`/刷新失败时清理认证状态并进入登录流程。独立联合测试覆盖初始化、过期和失败分支。
- [x] 标准 2：未登录访问受保护路由跳转 `/login` 并保留编码后的 redirect；已登录访问 `/login`、`/register` 跳转 `/applications`。独立测试在补齐显式 Token 与 user setup 后验证全部分支，未放宽断言。
- [x] 标准 3：logout 成功、HTTP 失败和网络错误均清理本地 Token 与 user；退出后路由守卫仍阻止进入受保护页面。独立测试覆盖三种 logout 失败/成功分支及认证边界。
- [x] 标准 4：并发 initialize 共享同一认证请求，初始化和 loading 状态不会发起重复认证请求。独立测试覆盖初始化去重和加载状态。
- [x] 标准 5：先有真实 RED，再由测试 Agent 独立复测。RED 报告记录公开 auth store/router 缺失导致 `9 failed`；实现说明状态为 `READY_FOR_TEST`；最终联合测试为 `16 passed`，报告状态为 `TEST_PASSED`。

## 回归与质量门禁

- [x] 独立复测同时覆盖 WEB-AUTH-001 token storage、Bearer、refresh 单次重试、并发队列和失败清理，结果与 WEB-AUTH-002 合计 `16 passed`。
- [x] RED、实现说明和通过报告的职责边界完整；通过报告确认测试 setup 修正仅建立契约要求的登录态，未修改生产实现 `frontend/src`，未放宽断言。
- [x] 本次项目管理验收仅修改 `docs/acceptance/` 和 `docs/tasks/`。

## 结论

WEB-AUTH-002 的 Pinia 认证状态、登录态恢复、初始化去重、路由保护、redirect 保留、logout 失败清理和初始化加载态均满足任务单及系统设计契约。项目管理验收结论为 `ACCEPTED`，任务状态设置为 `DONE`。
