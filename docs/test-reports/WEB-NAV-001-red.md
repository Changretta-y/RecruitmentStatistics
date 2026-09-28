# WEB-NAV-001 RED_CONFIRMED

- 测试角色：测试 Agent
- 环境：Windows; Node.js 20.19.0 (`.nvmrc`); npm 10.8.2; Playwright 1.63.x; Chromium
- 命令：`$env:PATH = 'C:\nvm4w\nodejs;' + $env:PATH; npx playwright test --config=tests/playwright.web_nav_001.config.mts`（工作目录：`frontend/`）
- 通过 / 失败：0 passed / 2 failed，退出码 1
- 公开输入：使用 UI 登录到 `/applications`，通过“日历”入口进入 `/calendar`；另一路由为登录后直接打开 `/calendar`。认证、投递列表和日历 API 由 Playwright 路由夹具响应。
- 期望行为：日历路由显示应用侧栏中的“投递”和“日历”导航项；点击“投递”可返回 `/applications` 并显示投递列表。
- 实际行为：应用页能显示投递导航项和日历入口；站内导航到 `/calendar` 后，投递导航项不再存在，断言失败。直接打开 `/calendar` 也无法找到投递导航项。失败页面快照仍显示日历标题、周/月视图控件和日历安排区域，说明路由、登录、日历页面与 API 夹具均已运行。
- 是否稳定复现：是。自动启动本地 Vite 后，一次专项运行中的两条独立路径均稳定因日历页缺少共享侧栏导航失败；不是服务器连接、认证、数据夹具或页面加载错误。
- 回归结果：无需扩展相邻回归。两条用例已覆盖站内进入、直接进入和返回投递页的公开契约；后续实现通过后将独立复测。
- 覆盖的验收标准：从投递页进入日历；直接打开日历；日历页保留投递导航入口并能返回投递列表；日历主内容仍可见。
- 未覆盖风险：本轮未验证移动端导航布局；任务明确将其排除。
- 黑盒声明：测试依据任务单和既有验收契约，仅观察浏览器公开路由、可访问 UI 和 mock API 行为，未读取或分析 `frontend/src/`。
