# WEB-AUTH-004 RED

- 状态：`RED_CONFIRMED`
- 测试角色：测试 Agent
- 环境：Windows；Node.js `v20.19.0`（与 `.nvmrc` 一致）；npm `10.8.2`；Vitest `4.1.11`。当前执行环境未提供 `nvm` 命令，未切换运行时；已确认现有 Node.js 版本与项目声明一致，依赖使用现有 `package-lock.json` 安装结果。
- 命令：`npm run test -- tests/test_web_auth_004.spec.ts --reporter=verbose`（连续运行两次）；`npm run test -- tests/test_web_auth_003.spec.ts --reporter=verbose`（相邻认证回归）
- 通过 / 失败：任务定向测试 `0 / 3`，连续两次结果一致；相邻认证回归 `7 / 0`。
- 公开输入：在 `1280px` 和 `375px` 视口契约下分别挂载登录页与注册页；直接访问 `/register`，填写有效注册表单后查询并激活可访问名称为“返回登录”的链接或按钮。
- 期望行为：登录页与注册页使用一致的、桌面端 `560px` 的可收缩认证容器；窄屏容器不使用超出可用宽度的固定宽度且根容器左右各至少保留 `16px`；注册页显示可见、可聚焦、不会提交表单的“返回登录”入口，激活后进入 `/login` 且不调用注册 API。
- 实际行为：登录页认证容器公开宽度值为 `480px`，未达到 `560px`；注册页同样未满足 `560px` 契约；注册页没有可按“返回登录”查询的链接或按钮，因此无法继续验证其聚焦、路由与不提交行为。
- 是否稳定复现：是。定向测试连续执行两次，均为相同的 3 项失败，失败值与失败入口一致。
- 回归结果：`WEB-AUTH-003` 登录/注册提交、校验、错误展示与注册成功跳转相关组件测试共 7 项全部通过。
- 覆盖的验收标准：桌面端登录与注册认证容器宽度一致且为 `560px ± 2px`；窄屏认证容器保持可收缩并预留左右间距的公开样式契约；注册页“返回登录”入口的可见性、可聚焦性、路由行为及不触发注册请求。
- 未覆盖风险：jsdom 不提供可靠的真实像素布局与横向滚动测量，本轮通过公开 DOM 样式契约验证响应式约束；待实现进入 `READY_FOR_TEST` 后仍应在可用浏览器环境中补充或执行 `1280px`、`375px` 的真实视口测量。
- 黑盒声明：未读取或分析生产实现代码。

## 失败摘要

1. `uses the same 560px desktop authentication width on login and register`：收到 `480px`，期望包含 `560px`。
2. `keeps both authentication surfaces shrinkable within a 375px viewport with 16px side gaps`：收到最大宽度 `480px`，期望 `560px` 的可收缩上限；后续无固定像素宽度及左右间距断言保留用于实现复测。
3. `is visible, keyboard focusable, routes to /login, and does not submit registration`：未找到可访问名称为“返回登录”的链接或按钮。
