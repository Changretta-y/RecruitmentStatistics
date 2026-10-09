# EXT-ROUTE-005 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/src/browser-extension/popup.html`、`popup.js`、`popup.css`；重新生成 `artifacts/recruitment-capture-extension-v0.2.0.zip`。
- 已实现行为：登录后默认显示“查看投递记录”和“新增投递”两个入口；记录列表与采集表单仅在进入相应页面时加载和显示，两个功能页可返回入口且互斥。返回保留当前登录态，退出清理列表、搜索、采集表单与导航状态。异步页面采集完成前若切换页面，旧导航请求不能把用户带回采集页。既有列表搜索、采集预览与保存逻辑保留。
- 视觉：沿用主站蓝色主按钮、浅色背景、白色圆角卡片与统一控件边框；补齐按钮 hover/focus 状态。移除固定弹窗最小高度，让双入口首页按内容收起；全部使用本地 CSS 和系统字体，无远程依赖。
- 数据库迁移：无。
- 配置变化：无；插件版本仍为 `0.2.0`。
- 已知限制：浏览器自检使用 Edge MV3 与本机合成 HTTP 替身；视觉布局未做不同浏览器的像素级比对。
- 自检环境：Windows；项目 Node.js 20.19.0（`.nvmrc`）；npm 10.8.2。
- 自检结果：`npm run build:extension` 成功，新 ZIP SHA-256 为 `B1BC49F2E6BEEA468CE5F0517CD7793C7CC6B075D4097550A5BBF455977E0ACD`；EXT-ROUTE-005 专项 7/7、EXT-ROUTE-004 版本回归 3/3 通过；`node --check` 对插件脚本通过。新旧 ZIP 中 `core.js`、`service-worker.js` 字节一致，保存匹配、认证与 URL/hash 核心逻辑未改。
- 建议复测命令：在仓库根目录运行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_005.config.ts --reporter=line`，并复测 EXT-ROUTE-004 版本套件。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：EXT-ROUTE-005
- 当前状态：READY_FOR_TEST
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：插件双入口与互斥功能页、统一视觉、更新的 v0.2.0 ZIP、本实现说明。
- 接收方工作范围：独立黑盒复测可加载插件的入口、功能与视觉交互，提交 TEST_PASSED 或 TEST_FAILED 报告。
- 输入文档：`docs/tasks/EXT-ROUTE-005.md`、`docs/test-reports/EXT-ROUTE-005-red.md`。
- 结果或风险：专项与版本相邻回归自检通过；仍需测试 Agent 独立复测。
- 本阶段完成条件：测试 Agent 完成复测并交项目管理 Agent 验收。
