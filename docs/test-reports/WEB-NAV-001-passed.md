# WEB-NAV-001 TEST_PASSED

- 测试角色：测试 Agent
- 环境：Windows；Node.js 20.19.0（`.nvmrc`）；npm 10.8.2；Playwright 1.63.x；Vitest 4.1.11
- 命令：
  - `npx playwright test --config=tests/playwright.web_nav_001.config.mts`（工作目录：`frontend/`）
  - `npm run test -- tests/test_web_cal_001.spec.ts`（工作目录：`frontend/`）
- 通过 / 失败：导航专项 2 passed / 0 failed；日历回归 11 passed / 0 failed；两条命令退出码均为 0
- 公开输入：通过 UI 登录后先进入 `/applications`，再点侧栏日历；另一路径直接打开 `/calendar`。测试用 Playwright API 路由夹具响应认证、投递列表和日历数据。
- 期望行为：日历页面保留投递与日历入口，日历内容可见；点击投递入口后进入 `/applications` 并显示投递列表。
- 实际行为：两种进入日历的路径下，投递入口和日历入口均可见；侧栏“投递”可返回 `/applications` 并显示投递进度标题。日历标题与内容控件正常显示。既有日历专项全数通过。
- 是否稳定复现：复测通过；Playwright 两条浏览器路径均通过，Vitest 日历回归 11/11 通过。
- 回归结果：WEB-CAL-001 日历专项 11/11 通过。
- 覆盖的验收标准：站内进入和直接打开日历；侧栏导航项可见；从日历返回投递列表；日历主内容及既有日历路由行为正常。
- 未覆盖风险：未测试窄屏导航抽屉；按任务范围不调整窄屏设计。
- 黑盒声明：独立复测仅观察浏览器公开路由、可访问 UI 和 API mock 行为；未读取或分析 `frontend/src/`。
