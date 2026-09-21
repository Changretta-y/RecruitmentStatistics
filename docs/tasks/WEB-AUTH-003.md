# WEB-AUTH-003 登录与注册页面

- 状态：`DONE`
- 用户价值：用户可通过可理解的页面完成注册、登录和错误修正。
- 范围：`RegisterView.vue`、`LoginView.vue`、表单校验、API 提交态、错误显示和成功跳转。
- 非范围：后端认证实现、Token 拦截器、投递列表页面、邮箱验证。
- 依赖：`WEB-AUTH-002`、`AUTH-001`、`AUTH-002`。
- 允许修改范围：测试 Agent：`frontend/tests/`、`tests/e2e/`、`docs/test-reports/`；实现 Agent：`frontend/src/`、前端依赖和 `docs/implementation-notes/`；项目管理 Agent：仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`。

## UI 契约

- 注册页字段：用户名 3～30、可选邮箱、密码至少 8、确认密码；前端先校验一致性，后端字段错误也要映射。
- 注册成功提示“注册成功，请登录”，不自动登录，跳转登录页。
- 登录页字段用户名、密码；提交期间按钮禁用并显示 loading；成功保存 Token/user 后进入 `/applications` 或原 redirect。
- `401 INVALID_CREDENTIALS` 以不枚举用户的通用提示展示；网络/500 保留输入并提供重试。

## 验收标准

- [x] 注册字段、密码一致性、提交禁用和后端字段错误显示正确。
- [x] 注册成功跳登录，不产生自动登录状态。
- [x] 登录成功跳投递页；错误凭据不泄露用户是否存在。
- [x] 已登录用户访问登录/注册页被路由规则重定向。
- [x] 组件测试先 RED，且与 `WEB-AUTH-002`、后端契约独立复测通过。

## 风险与测试边界

- 不在页面中直接操作 localStorage；Token 行为由 `WEB-AUTH-001` 测试。
- UI 可用 Element Plus 或原生控件，但可访问 label、错误文本和按钮状态必须可观测。
