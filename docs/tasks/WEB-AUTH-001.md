# WEB-AUTH-001 Token 存储与 Axios 自动刷新

- 状态：`DONE`
- 用户价值：浏览器能安全复用登录凭据，并在 Access Token 过期时自动完成一次刷新和原请求重试。
- 范围：`token-storage.ts`、public/auth Axios client、Bearer 注入、401 刷新队列、7 天过期清理。
- 非范围：后端 JWT 签发、Pinia 用户状态、路由守卫、登录/注册页面。
- 依赖：`AUTH-003`、`AUTH-004`、`BASE-ENV-001`。
- 允许修改范围：测试 Agent：`frontend/tests/`、`tests/e2e/`、`docs/test-reports/`；实现 Agent：`frontend/src/`、前端运行时依赖和 `docs/implementation-notes/`；项目管理 Agent：仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`。

## 业务规则与公开契约

- Token 只能由统一模块使用 `localStorage` 保存/读取/清除，结构含 `accessToken`、`refreshToken`、`expiresAt`。
- 受保护请求自动添加 `Authorization: Bearer <access>`；刷新接口不得再次触发刷新拦截器。
- 401 时单次刷新任务全局去重，并发失败请求进入等待队列；刷新成功更新轮换 Token 并各自只重试一次。
- 无 Refresh Token、超过本地 7 天截止时间、刷新失败或刷新接口 401：清空 Token，拒绝等待请求并导航登录页。

## 验收标准

- [x] 存储工具能保存、读取、判断 7 天过期和清除，组件不直接读写 localStorage。
- [x] 请求注入 Bearer；401 只发一个 refresh，并成功重试原请求一次。
- [x] 并发 401 共用刷新结果；刷新接口自身不会无限循环。
- [x] 刷新失败后 Token、等待请求和认证错误状态被清理。
- [x] Vitest/组件测试先形成 RED，独立复测覆盖分支边界。

## 风险与测试边界

- localStorage 的 XSS 风险由 `SEC-001` 的安全配置和代码检查约束；本任务不改为 Cookie。
- 认证 Store 如何消费清理事件由 `WEB-AUTH-002` 负责。
