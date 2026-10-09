# EXT-ROUTE-004 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/src/browser-extension/manifest.json`、`frontend/src/browser-extension/README.md`、`scripts/build-extension.mjs` 与新交付包 `artifacts/recruitment-capture-extension-v0.2.0.zip`。
- 已实现行为：插件 Manifest 版本为 `0.2.0`，构建入口和使用说明均指向同名 `v0.2.0` ZIP；包内 Manifest 亦为 `0.2.0`。旧 `v0.1.0` 包作为历史文件保留，构建入口不再生成该版本。业务逻辑、API 与插件权限未改。
- 数据库迁移：无。
- 配置变化：仅插件版本与交付文件名。
- 已知限制：交互自检使用本机合成 HTTP 替身，未访问真实账号或线上数据。
- 自检环境：Windows；项目 Node.js 20.19.0（`.nvmrc`）；npm 10.8.2。
- 自检结果：`node --check` 对构建脚本及插件三个 JS 文件通过；`npm run build:extension` 两次成功且 ZIP SHA-256 一致，为 `C67185D84D3692472533FFDC2DB8D3BB4574D969616E6D061B13B4C09F915D91`；EXT-ROUTE-004 专项 3/3 通过。
- 建议复测命令：在仓库根目录运行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_004.config.ts --reporter=line`。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：EXT-ROUTE-004
- 当前状态：READY_FOR_TEST
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：插件 v0.2.0 版本声明、打包入口、使用说明和可加载 ZIP。
- 接收方工作范围：独立黑盒复测交付 ZIP 版本与既有插件交互，提交 TEST_PASSED 或 TEST_FAILED 报告。
- 输入文档：`docs/tasks/EXT-ROUTE-004.md`、`docs/test-reports/EXT-ROUTE-004-red.md`。
- 结果或风险：专项自检通过；仍需测试 Agent 独立复测。
- 本阶段完成条件：测试 Agent 完成复测并交项目管理 Agent 验收。
