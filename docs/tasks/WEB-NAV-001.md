# WEB-NAV-001 日历页保留主侧边栏导航

- 状态：`DONE`
- 用户价值：用户可以从日历页的主侧边栏返回投递页面，避免进入日历后失去应用内导航。
- 范围：认证状态下日历路由的主布局与从侧边栏返回投递列表的可观察行为。
- 非范围：修改日历时间轴或事件数据、未登录重定向策略、移动端导航重新设计。
- 依赖：`WEB-CAL-001`、`WEB-APP-005` 已完成。
- 允许修改范围：项目管理 Agent 仅 `docs/tasks/`、`docs/acceptance/`；测试 Agent 仅 `frontend/tests/`、`docs/test-reports/`；实现 Agent 仅 `frontend/src/`、`docs/implementation-notes/`。

## 业务规则与公开契约

- 登录用户打开 `/calendar` 时，应用主侧边栏仍显示；侧边栏至少包含“投递”和“日历”导航项。
- 用户可从日历页激活“投递”导航项，路由切换至 `/applications` 并显示投递列表。
- 通过站内导航和直接打开/刷新 `/calendar` 均需满足同一布局契约。
- 日历内容、周/月视图与事件交互保持既有行为；导航修复不得移除或遮挡日历主内容。

## 输入、输出与错误行为

- 输入：已认证用户进入 `/calendar`，再通过公开侧边栏操作导航。
- 输出：可见的共享侧边栏；选择“投递”后 URL 为 `/applications` 且投递页呈现。
- 未登录访问仍按现有认证路由策略处理，不在本任务调整。

## 验收标准

- [x] 从 `/applications` 进入日历后，侧边栏与“投递”“日历”入口可见。
- [x] 日历侧边栏“投递”入口可用，操作后进入 `/applications`。
- [x] 直接打开日历路由时仍显示同一侧边栏，日历主内容仍可见。
- [x] 日历既有路由和认证回归通过。

## 风险与测试边界

- 测试只通过公开路由和可访问 UI 元素观察，不依赖具体 Vue 组件树或实现布局结构。
- 先证明当前版本在日历页缺少导航行为，再交实现角色修复；修复后由测试角色独立复测。

## Agent 交接

- 任务编号：`WEB-NAV-001`
- 当前状态：`DONE`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent
- 已完成内容与产物：RED 测试 `frontend/tests/test_web_nav_001.e2e.spec.ts`、Playwright 配置 `frontend/tests/playwright.web_nav_001.config.mts`、RED 报告 `docs/test-reports/WEB-NAV-001-red.md`；实现说明 `docs/implementation-notes/WEB-NAV-001.md`；独立通过报告 `docs/test-reports/WEB-NAV-001-passed.md`。测试 Agent 专项 2/2、WEB-CAL-001 回归 11/11 通过。
- 测试范围限制：未测试窄屏导航抽屉；依任务范围保留原行为。
- 验收结论：项目管理 Agent 按 `docs/acceptance/WEB-NAV-001.md` 完成逐项验收并设置为 `DONE`。
