# WEB-AUTH-002 Pinia 认证状态与路由保护

- 状态：`DONE`
- 用户价值：刷新页面后登录态可恢复，未登录用户不能进入投递页面。
- 范围：Pinia auth store、`initialize/fetchMe/logout`、路由守卫、初始化加载态和 redirect query。
- 非范围：Token 底层刷新算法、登录/注册表单视觉交互。
- 依赖：`WEB-AUTH-001`、`AUTH-002`、`AUTH-004`。
- 允许修改范围：测试 Agent：`frontend/tests/`、`tests/e2e/`、`docs/test-reports/`；实现 Agent：`frontend/src/`、`docs/implementation-notes/`；项目管理 Agent：仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`。

## 业务规则与公开契约

- Store 状态至少含 `user`、`initialized`、`loading`；Token 不复制到 Pinia 持久化状态。
- 应用启动从统一存储读取 Token；7 天过期立即清空，否则调用 `/api/v1/auth/me/`，必要时由 HTTP 层刷新。
- 未登录进入 `meta.requiresAuth=true` 页面跳转 `/login?redirect=<原地址>`；已登录访问登录/注册跳 `/applications`。
- `logout()` 无论接口成功、失败或网络错误都清理本地 Token 和 user，再跳转登录页。
- 初始化期间显示全屏加载，初始化完成后才决定路由，避免未授权闪烁。

## 验收标准

- [x] 登录态初始化成功后 user 可用，过期/刷新失败进入登录页。
- [x] 受保护路由、登录/注册路由跳转规则符合契约并保留 redirect。
- [x] 退出接口失败时本地状态仍清理，后退不能重新进入受保护页面。
- [x] 初始化和 loading 状态不会发起重复认证请求。
- [x] Store、路由和失败分支测试先 RED 后独立复测。

## 风险与测试边界

- 页面具体表单由 `WEB-AUTH-003`；列表路由目标由 `WEB-APP-002` 消费。
- 测试使用公开 Store/路由行为和 mock API，不分析后端实现。
