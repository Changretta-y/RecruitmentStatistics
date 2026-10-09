# EXT-ROUTE-006 RED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；项目 Node.js 20.19.0、npm 10.8.2；Edge MV3 无头持久上下文；从当前 `artifacts/recruitment-capture-extension-v0.2.0.zip` 解包加载插件，HTTP 全部由本机合成替身截获。
- 命令（仓库根目录）：`npm exec -- playwright test --config=tests/e2e/playwright.ext_route_006.config.ts --reporter=line`
- 通过 / 失败：新专项 5 项，2 通过、3 失败，退出码 1；三项目标用例单独复跑仍因同一默认视图行为失败。
- 公开输入：合成账号登录、无效登录、顶部“查看投递记录”/“新增投递”切换、记录搜索和刷新、采集预览及 POST 保存、退出登录。
- 期望行为：成功登录立即显示新增投递采集表单，两切换按钮固定在功能区上方且当前视图有可观察的选中状态；点击记录/新增直接互斥切换，不出现返回入口；登录态、搜索/刷新、保存和退出继续正常。
- 实际行为：合成登录成功，`#company-name` 输入框存在但隐藏，弹窗仍停在 EXT-ROUTE-005 的双入口首页。默认新增、顶部互斥切换及默认采集保存三项都在公开表单可见性断言失败。无效登录隔离、旧入口下的记录搜索/刷新两项通过。失败不是 ZIP、浏览器、认证或 HTTP 夹具错误。
- 是否稳定复现：是；完整专项与目标三项单独复跑均在相同的默认采集可见性断言失败。
- 回归结果：`npm exec -- playwright test --config=tests/e2e/playwright.ext_route_005.config.ts --reporter=line` 为 7 通过、0 失败，证明当前 ZIP 的旧入口、记录搜索、采集预览/保存和退出链路正常。新专项中的旧记录搜索/刷新与无效登录 2/2 通过。
- 覆盖的验收标准：登录默认采集、顶部双按钮和选中状态、两视图互斥直达、无返回入口、认证、记录搜索/刷新、保存及退出回归。
- 未覆盖风险：目标默认采集尚未出现，后续选中状态及切换断言须待实现后完整复测；本次未做像素级视觉或真实后端联调。
- 黑盒声明：未读取或分析生产实现代码；只观察可加载 ZIP 的弹窗 DOM、交互和公开 HTTP 请求。

## Agent 交接

- 任务编号：EXT-ROUTE-006
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：功能实现 Agent
- 已完成内容与产物：`tests/e2e/ext_route_006.spec.ts`、`tests/e2e/playwright.ext_route_006.config.ts` 与本报告。
- 接收方工作范围：仅插件生产实现、v0.2.0 交付 ZIP 和实现说明；保持测试、断言及质量门槛不变。
- 输入文档：`docs/tasks/EXT-ROUTE-006.md`、本报告。
- 建议命令：在仓库根目录执行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_006.config.ts --reporter=line`，并核对版本与相邻业务回归。
- 结果或风险：目标默认导航缺失稳定 RED，当前插件原有功能正常。
- 本阶段完成条件：实现交 `READY_FOR_TEST` 后由测试 Agent 独立复测。
