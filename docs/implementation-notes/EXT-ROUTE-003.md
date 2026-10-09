# EXT-ROUTE-003 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/src/browser-extension/` 的弹窗、样式与后台消息；重新生成 `artifacts/recruitment-capture-extension-v0.1.0.zip`。
- 已实现行为：登录后经现有认证客户端分页读取当前用户 `/api/v1/applications/`；后台只向弹窗返回公司名和岗位名，按公司 ID（缺失时按规范化名称）聚合。弹窗显示公司数量、岗位摘要，支持公司/岗位不区分大小写搜索及手动刷新；加载、无记录、无匹配、认证失效和网络失败分别提示，网络失败可重试。退出时清除列表与搜索，并忽略已退出账号的迟到响应。列表失败或刷新不会清除采集草稿。
- 既有基线：`core.js` 中 EXT-ROUTE-001 已验证的 URL/hash 保留修复在本任务开始前处于未提交状态。本次仅将该既有 hunk 与重新打包的 ZIP 一并提交，保持可维护源码与交付包一致；本任务没有改变保存匹配或 URL/hash 规则。
- 数据库迁移：无。
- 配置变化：无。
- 已知限制：自检使用本机合成 HTTP 替身和 Edge 插件环境，未访问真实用户数据或线上招聘站点。
- 自检环境：Windows；项目 Node.js 20.19.0（`.nvmrc`）；npm 10.8.2。
- 自检结果：`node --check` 对 `core.js`、`popup.js`、`service-worker.js` 均通过；`npm run build:extension` 通过，ZIP SHA-256 为 `72E0D99A65F77F3C1ABA0227062773B51147BA18CD6176889AC75EF9243A0B97`；EXT-ROUTE-003 7/7、EXT-ROUTE-002 7/7、EXT-ROUTE-001 7/7 通过。
- 建议复测命令：在仓库根目录执行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_003.config.ts --reporter=line`，再运行 EXT-ROUTE-002 与 EXT-ROUTE-001 配置。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：EXT-ROUTE-003
- 当前状态：READY_FOR_TEST
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：插件已投递公司列表、重新打包的 ZIP、本实现说明。
- 接收方工作范围：独立检查交付 ZIP 的公开弹窗行为并提交 TEST_PASSED 或 TEST_FAILED 报告。
- 输入文档：`docs/tasks/EXT-ROUTE-003.md`、`docs/test-reports/EXT-ROUTE-003-red.md`。
- 结果或风险：专项与相邻回归自检通过；仍需测试 Agent 独立复测。
- 本阶段完成条件：测试 Agent 完成复测并交项目管理 Agent 验收。
