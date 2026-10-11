# EXT-ROUTE-007 RED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；Node.js 20.19.0、npm 10.8.2、uv 0.7.21；Edge MV3 无头持久上下文；合成登录与本机 HTTP 替身。测试只解包公开交付 ZIP，并对照 `frontend/public/logo.png` 的原始字节，不读取插件生产源码。
- 命令（仓库根目录）：`npm exec -- playwright test --config=tests/e2e/playwright.ext_route_007.config.ts --reporter=line`
- 通过 / 失败：新专项 4 项，2 通过、2 失败，退出码 1；完整命令复跑得到相同结果。
- 公开输入：当前 Git HEAD 跟踪的 `artifacts/recruitment-capture-extension-v0.2.0.zip`、包内 Manifest、平台公开 Logo 文件及合成登录弹窗。
- 期望行为：Manifest 的 `icons` 与 `action.default_icon` 均指向包内 Logo，所指文件字节与 `frontend/public/logo.png` 完全一致；版本保持 `0.2.0` 且插件仍可加载登录。
- 实际行为：包内 Manifest `version` 为 `0.2.0`，Edge MV3 可加载并以合成账号进入采集视图，两项通过；`icons` 与 `action.default_icon` 均为未定义，两个图标契约测试失败。由于没有图标引用，包内字节一致性断言尚未到达，需实现后完整复测。
- 是否稳定复现：是；两次完整运行均为相同的 2 失败、2 通过。ZIP 解包、版本、浏览器、合成认证均正常，失败来自缺失图标声明。
- 回归结果：本套件现有登录/默认采集行为 1/1 通过。
- 覆盖的验收标准：扩展图标与 action 工具栏图标声明、包内文件存在且与平台 Logo 字节相同、版本保持及登录回归。
- 未覆盖风险：工作树中的 `v0.2.0` ZIP 当前被其他未提交改动标记删除，测试在缺失时只读读取 HEAD Git 对象中的同名已提交 ZIP 作为稳定基线；实现交付时应恢复/更新实际工作树交付包。平台 Logo 源文件存在；由于 Manifest 尚无引用，本轮未执行 Logo 字节比对。未联调真实后端。
- 黑盒声明：未读取或分析生产实现代码；未修改插件源码、ZIP、平台 Logo 或测试门槛。

## Agent 交接

- 任务编号：EXT-ROUTE-007
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：功能实现 Agent
- 已完成内容与产物：`tests/e2e/ext_route_007.spec.ts`、`tests/e2e/playwright.ext_route_007.config.ts` 与本报告。
- 接收方工作范围：仅插件图标、构建产物及实现说明；保持测试、断言和质量门槛不变。
- 输入文档：`docs/tasks/EXT-ROUTE-007.md`、本报告。
- 建议命令：在仓库根目录执行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_007.config.ts --reporter=line`；实现提交后应同时检查实际 ZIP 文件存在。
- 结果或风险：当前已提交包缺图标声明而稳定 RED；工作树同名 ZIP 缺失为独立交付状态，不能将其误计为图标 RED。
- 本阶段完成条件：实现交 `READY_FOR_TEST` 后由测试 Agent 独立复测。
