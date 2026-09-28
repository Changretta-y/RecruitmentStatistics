# EXT-AUTH-001 实现说明

- 状态：READY_FOR_TEST
- 修改范围：恢复 `frontend/src/browser-extension/`；修正插件默认 API origin、Manifest host permissions 和弹窗服务器选项；更新根 README 与插件 README；新增 `scripts/build-extension.mjs` 并在根 `package.json` 提供 `build:extension`；生成 `artifacts/recruitment-capture-extension-v0.1.0.zip`。
- 已实现行为：默认 origin 为 `http://115.190.240.84:5173`；本地 Vite 选项为 `127.0.0.1:5173` 与 `localhost:5173`。登录、refresh、me、logout、应用列表/创建/更新都使用相同 origin 下的 `/api/v1/...` 路径，源码不再引用旧 `:8000` origin。Manifest host permissions 与上述三个 origin 对应。
- 源码恢复：从既有归档恢复 7 个文件；恢复前确认归档与已有忽略目录中的每个文件 SHA-256 一致。可维护源码现位于 `frontend/src/browser-extension/`。
- 打包：`npm run build:extension` 只从可维护源码打包 Manifest V3 所需的 6 个运行文件，不包含 README、测试数据或目录外文件；输出 ZIP 根目录直接包含 manifest。ZIP 使用固定元数据与 Node 内置 zlib/文件 API，无新增依赖。
- 数据库迁移：不适用。
- 配置变化：根 `package.json` 增加 `build:extension` 命令；无依赖或锁文件变化。
- 自检环境：Windows PowerShell，nvm Node.js 20.19.0，npm 10.8.2。
- 自检结果：`npm run build:extension` 连续构建两次，ZIP SHA-256 均为 `88253F0ED5AD02B81906AE3A66FA5035C66D4C82C55A9824A4037758BC4B9A9E`；归档可由 ZIP reader 打开，6 个文件集合与源码逐项 SHA-256 匹配。`node --check` 对三个 JavaScript 文件通过。公开 `GET http://115.190.240.84:5173/api/v1/health/` 返回 `200 application/json`。
- E2E 自检：`npm run test:ext-auth` 结果 `3 passed, 4 failed`。通过项覆盖 Manifest origin、弹窗初始服务器选项和源码打包重复性；其余 4 项在持久化 Chromium 启动前失败，错误为 Windows Playwright `spawn UNKNOWN`，没有执行合成登录/刷新/me/应用 UI 流程。没有使用真实凭据，也没有把隔离 stub 当作真实 Django 认证证据。测试 Agent需按 RED 报告记录的环境阻塞独立复测，不能将其记作功能通过。
- 已知限制：本环境无法启动完整 Chrome for Testing，因此本轮未验证真实 MV3 加载和登录流程。公开健康接口仅证明平台入口可用，不证明插件认证集成。
- 建议复测命令：在 Chromium 可启动的 Windows 环境从仓库根目录执行 `npm run test:ext-auth`；并执行 `npm run build:extension` 后核对归档内容集合及文件 SHA。
- 测试完整性声明：未修改任何测试文件、脚本、断言、测试报告或质量门槛。

## Agent 交接

- 任务编号：`EXT-AUTH-001`
- 当前状态：`READY_FOR_TEST`
- 发送角色：功能实现 Agent
- 接收角色：原测试 Agent `share_tests`
- 已完成内容与产物：源码 `frontend/src/browser-extension/`、根 README 与构建入口、可重复生成的指定 ZIP、本文实现说明。
- 接收方工作范围：只读独立复测默认 origin、Manifest 权限、认证/API URL、ZIP 文件集合与内容、凭据脱敏；不修改生产实现。
- 输入文档：`docs/tasks/EXT-AUTH-001.md`、`docs/test-reports/EXT-AUTH-001-red.md`、系统设计认证及 API 公开契约。
- 建议命令：`npm run test:ext-auth`；受阻项须区分 Chromium 环境错误与业务断言结果。
- 结果或风险：公开配置/初始弹窗/构建回归通过；完整 MV3 登录链路等待修复或排除 Windows Chromium 启动阻塞后由测试 Agent复测。
- 本阶段完成条件：测试 Agent收到源码、命令与当前环境限制后独立复测；不得将 READY_FOR_TEST 改成 TEST_PASSED 或 DONE。
