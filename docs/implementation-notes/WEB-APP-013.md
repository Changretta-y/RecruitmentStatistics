# WEB-APP-013 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/src/views/ApplicationsView.vue`。
- 已实现行为：合法 HTTP(S) 招聘地址由公司名作为唯一可见链接文本，保留原地址并在新窗口打开；无地址或非法协议显示普通公司名。搜索建议通过 Teleport 呈现在页面顶层，随输入框定位并响应窗口滚动和尺寸变化；页面外点击关闭，输入框、建议项和重试按钮的内部点击保持原有行为。
- 数据库迁移：无。
- 配置变化：无。
- 已知限制：本次自检使用公开 HTTP 替身，未访问真实招聘网站。
- 自检环境：Windows；Node.js 20.19.0（`.nvmrc`）；npm 10.8.2。
- 自检结果：`npm exec -- playwright test --config=tests/playwright.web_app_013.config.mts` 8/8；WEB-APP-008 3/3；APP-012 3/3；`npm run lint`、`npm run build` 均通过。
- 建议复测命令：在 `frontend/` 运行 `npm exec -- playwright test --config=tests/playwright.web_app_013.config.mts`，并复测 WEB-APP-008、APP-012 套件。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：WEB-APP-013
- 当前状态：READY_FOR_TEST
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：公司链接、建议浮层和外部点击修复；本实现说明。
- 接收方工作范围：独立黑盒复测并提交 TEST_PASSED 或 TEST_FAILED 报告。
- 输入文档：`docs/tasks/WEB-APP-013.md` 与 RED 报告 `docs/test-reports/WEB-APP-013-red.md`。
- 结果或风险：相关专项及相邻回归自检通过；仍需测试 Agent 独立复测。
- 本阶段完成条件：测试 Agent 复测完成并交项目管理 Agent 验收。
