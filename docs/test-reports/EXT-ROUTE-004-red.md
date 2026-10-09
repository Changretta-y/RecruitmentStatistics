# EXT-ROUTE-004 RED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；Node.js 20.19.0（`.nvmrc`）、npm 10.8.2、uv 0.7.21；Edge MV3 无头插件上下文。测试仅解包现有交付 ZIP 并通过本机合成 HTTP 替身完成登录，不使用真实账号或线上数据。
- 命令（在仓库根目录执行）：`npm exec -- playwright test --config=tests/e2e/playwright.ext_route_004.config.ts --reporter=line`
- 通过 / 失败：3 项中 1 通过、2 失败，退出码 1；同一命令复跑得到相同结果。
- 公开输入：从 `artifacts/` 中选择当前交付插件 ZIP，解包并读取包内 Manifest；用合成账号在加载后的弹窗登录。
- 期望行为：交付文件名为 `recruitment-capture-extension-v0.2.0.zip`，包内 Manifest `version` 为 `0.2.0`；既有登录进入采集视图行为继续可用。
- 实际行为：当前交付文件名仍为 `recruitment-capture-extension-v0.1.0.zip`，包内 Manifest `version` 仍为 `0.1.0`，两项版本断言失败；合成登录及采集视图回归通过。
- 是否稳定复现：是，完整三项测试两次运行均为相同的 2 失败、1 通过。ZIP 可解包、Edge 可加载、登录 HTTP 替身正常；失败由缺失版本升级导致。
- 回归结果：同套件既有登录/进入采集视图行为 1/1 通过。版本修复后该回归会自动改为加载 `v0.2.0` 交付 ZIP。
- 覆盖的验收标准：公开 ZIP 文件名、包内 Manifest 版本与一项现有插件交互行为。
- 未覆盖风险：测试角色不读取插件生产源码、构建脚本或 README；这三处版本一致性由实现说明和项目管理验收核对。尚未执行全部插件业务回归。
- 黑盒声明：未读取或分析生产实现代码；只观察可加载交付 ZIP、Manifest 和公开弹窗行为。

## Agent 交接

- 任务编号：EXT-ROUTE-004
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：功能实现 Agent
- 已完成内容与产物：`tests/e2e/ext_route_004.spec.ts`、`tests/e2e/playwright.ext_route_004.config.ts` 与本报告。
- 接收方工作范围：仅按任务单更新版本相关生产文件、构建产物与实现说明；测试目录、断言和门槛只读。
- 输入文档：`docs/tasks/EXT-ROUTE-004.md`、本报告。
- 建议命令：在仓库根目录运行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_004.config.ts --reporter=line`。
- 结果或风险：现有 `0.1.0` 交付稳定 RED，旧登录行为通过。
- 本阶段完成条件：实现交 `READY_FOR_TEST` 后由测试 Agent 独立复测。
