# EXT-ROUTE-006 TEST_PASSED

- 测试角色：测试 Agent
- 复测对象：实现与可加载 `v0.2.0` ZIP 提交 `f3e8593`；复测时 HEAD 为任务交接文档提交 `e7f0865`。
- 环境：Windows；Node.js 20.19.0、npm 10.8.2；Edge MV3 无头持久上下文；测试从 `artifacts/recruitment-capture-extension-v0.2.0.zip` 解包加载插件，认证及应用 HTTP 均由本机合成替身处理。
- 命令与结果（仓库根目录）：
  - `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_006.config.ts --reporter=line`：5 通过、0 失败，退出码 0。
  - `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_005.config.ts --grep "signed-out popup|existing current-user record search|existing capture preview" --reporter=line`：仍适用的 3 项通过、0 失败，退出码 0。
  - `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_004.config.ts --reporter=line`：版本与登录 3 通过、0 失败，退出码 0。
- 公开输入：合成账号/错误凭据；登录后默认视图；顶部“查看投递记录”和“新增投递”按钮；列表搜索/刷新、采集预览/POST 保存、退出登录。
- 期望行为与实际行为：登录后直接显示采集表单，两按钮位于功能区上方，无入口页或返回按钮；当前按钮有可观察的选中外观。点击记录和新增可直接互斥切换、保留登录态；记录搜索/刷新、采集保存、无效登录和退出清理均通过。原 RED 三项转绿。
- 是否稳定复现：本次独立完整与适用回归共 11 项通过，可加载 ZIP、Edge MV3、认证和合成 HTTP 正常。
- 回归结果：EXT-ROUTE-005 的认证隔离、已投递记录搜索及旧采集保存 3/3；EXT-ROUTE-004 的 ZIP 文件名、Manifest `0.2.0` 与合成登录 3/3。EXT-ROUTE-005 中要求“默认入口首页”和“返回入口”的其余 4 项已被 EXT-ROUTE-006 新契约替代，未作为当前行为回归执行。
- 覆盖的验收标准：默认新增、顶部双按钮、选中态、互斥直达、无返回入口、登录态与搜索/刷新/保存/退出回归、v0.2.0 ZIP 可加载。
- 未覆盖风险：未进行像素级视觉比较或真实后端联调；URL/hash 全套不在本次指定回归命令内。
- 黑盒声明：未读取或分析生产实现代码；未修改插件源码、ZIP、测试断言或质量门槛。

## Agent 交接

- 任务编号：EXT-ROUTE-006
- 当前状态：`TEST_PASSED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent
- 已完成内容与产物：对 v0.2.0 交付 ZIP 的独立黑盒复测与本报告。
- 接收方工作范围：核对任务契约、RED 报告、实现说明与本报告后验收。
- 输入文档：`docs/tasks/EXT-ROUTE-006.md`、`docs/test-reports/EXT-ROUTE-006-red.md`。
- 结果或风险：新导航及适用回归 11/11 通过；像素级视觉和真实服务联调未覆盖。
- 本阶段完成条件：项目管理 Agent 验收并裁定任务状态。
