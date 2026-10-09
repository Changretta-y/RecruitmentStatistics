# EXT-ROUTE-006 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/src/browser-extension/popup.html`、`popup.js`、`popup.css`；重新生成 `artifacts/recruitment-capture-extension-v0.2.0.zip`。
- 已实现行为：登录或恢复会话后先完成当前页面采集，直接显示新增投递表单；账号栏下方始终显示“查看投递记录”和“新增投递”两个切换按钮。记录与采集视图互斥，选中按钮通过 `aria-pressed` 和蓝色样式明确标识。移除 EXT-ROUTE-005 的入口首页及返回按钮；切换仍保留登录态、搜索内容和未保存的采集输入，退出清理状态。
- 视觉：顶部导航在弹窗滚动时保持可见，沿用本地 CSS 的主站蓝色、白卡片、圆角及 hover/focus 样式；未引入远程依赖。
- 数据库迁移：无。
- 配置变化：无；插件版本仍为 `0.2.0`。
- 已知限制：自检使用 Edge MV3 与本机合成 HTTP 替身，没有真实账号或线上服务联调。EXT-ROUTE-005 中要求默认入口首页的断言已由本任务新契约替代；仅运行其中仍适用的相邻行为测试。
- 自检环境：Windows；项目 Node.js 20.19.0（`.nvmrc`）；npm 10.8.2。
- 自检结果：`npm run build:extension` 成功，新 ZIP SHA-256 为 `C7150C8EE8EDFA135E8EB063FA77D82BDD8DD879DC24B0605F978D9C504B1824`；EXT-ROUTE-006 5/5，EXT-ROUTE-005 的认证/记录搜索/采集保存 3/3，EXT-ROUTE-004 版本套件 3/3；`node --check` 通过。`core.js`、`service-worker.js` 与 Manifest 未改，保存匹配、认证和 URL/hash 核心逻辑保持原样。
- 建议复测命令：在仓库根目录执行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_006.config.ts --reporter=line`，并运行仍适用的 EXT-ROUTE-005 业务回归及 EXT-ROUTE-004 版本套件。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：EXT-ROUTE-006
- 当前状态：READY_FOR_TEST
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：顶部双按钮与默认采集视图、更新的 v0.2.0 ZIP、本实现说明。
- 接收方工作范围：独立黑盒复测可加载插件的视图切换、选中状态、搜索/保存/认证回归并提交 TEST_PASSED 或 TEST_FAILED 报告。
- 输入文档：`docs/tasks/EXT-ROUTE-006.md`、`docs/test-reports/EXT-ROUTE-006-red.md`。
- 结果或风险：专项与相邻有效回归自检通过；仍需测试 Agent 独立复测。
- 本阶段完成条件：测试 Agent 完成复测并交项目管理 Agent 验收。
