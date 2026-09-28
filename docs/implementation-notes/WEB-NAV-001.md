# WEB-NAV-001 实现说明

## 改动

- 新增 `frontend/src/components/AppShell.vue`，将投递页原有的应用栏、侧边导航、通知设置入口、用户名和退出行为抽成可复用主布局。
- 投递页与日历页共用该布局。日历周/月控件、事件时间轴和事件详情仍由 `CalendarView.vue` 渲染。
- 桌面端侧栏保持展开，支持在日历页直接点击“我的投递进度”返回 `/applications`；窄屏继续使用原来的临时抽屉和菜单按钮。
- 保留当前路由认证守卫以及抽屉内“日历”“新增投递”入口。

## 验证

- 环境：Windows；Node.js 20.19.0（`.nvmrc`）；npm 10.8.2；Playwright 1.63.x；Chromium。
- `npx playwright test --config=tests/playwright.web_nav_001.config.mts`：2 passed。覆盖从投递页进入日历并返回、直接打开日历，以及页面导航和日历内容可见。
- `npm run lint`：通过。
- `npm run build`：通过。
- Vite 输出已有的 `configLoader: 'native'` 提示；Playwright 浏览器控制台有现存 Vue Router `next()` 弃用提示，均未阻断验证。

## 限制

- 按任务范围未调整窄屏导航设计；在窄屏下侧栏仍需通过菜单按钮打开。
- 未改测试、任务单或 RED 报告。请测试 Agent 独立复测，并由项目管理角色更新任务状态。
