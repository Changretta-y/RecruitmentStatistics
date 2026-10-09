# EXT-ROUTE-003 RED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；项目 Node.js 20.19.0（`.nvmrc`）、npm 10.8.2；Edge MV3 无头持久上下文；从现有可加载交付 ZIP 解包插件；全部 HTTP 经 `127.0.0.1` 合成替身截获，不访问线上账号或数据。解包命令使用后端冻结环境的 uv 0.7.21。
- 命令（在仓库根目录执行）：`npm exec -- playwright test --config=tests/e2e/playwright.ext_route_003.config.ts --reporter=line`
- 通过 / 失败：新专项 1 通过、6 失败，共 7 项；退出码 1。单独复跑列表与搜索两项，均在同一缺失行为断言失败。
- 公开输入：合成账号登录插件采集弹窗；HTTP 替身返回当前用户两页投递（同公司重复记录和不同岗位）、空列表、401、网络断开及刷新后变更数据；模拟公司名/岗位名搜索、手动刷新和退出。
- 期望行为：登录后显示“已投递公司”列表、公司/岗位摘要、去重结果数，分页取全；搜索忽略大小写，清空恢复全部；刷新重新读取；空、认证失效和网络失败有明确状态及重试，采集草稿不丢；退出清理列表与搜索。
- 实际行为：未登录状态不请求应用列表（通过）；合成登录和原采集表单正常，但弹窗没有“已投递公司”区域，也未自动发起列表 GET。列表/搜索/刷新/空结果/401/退出六项因此稳定失败。失败发生在公开 DOM 文本或列表请求断言，非 ZIP、浏览器、登录、HTTP 替身或测试执行错误。
- 是否稳定复现：是；完整专项两次运行均为 1 通过、6 失败，目标列表与搜索还单独复跑，同一公开缺失行为失败。
- 回归结果：`npm exec -- playwright test --config=tests/e2e/playwright.ext_route_002.config.ts --reporter=line` 为 7/7 通过；`npm exec -- playwright test --config=tests/e2e/playwright.ext_route_001.config.ts --reporter=line` 为 7/7 通过。现有插件保存、多岗位匹配、URL/hash 采集和失败登录链路正常。
- 覆盖的验收标准：未登录不读取、认证列表与分页/重复公司聚合、公司/岗位过滤及无匹配、刷新、空/401/网络状态、草稿保留、退出清理、私有字段不展示与不写入、原采集表单可用。
- 未覆盖风险：由于新增列表入口尚不存在，各失败用例的后续交互断言尚未执行；实现后必须完整复测。HTTP 为合成替身，未接真实后端或真实用户。
- 黑盒声明：未读取或分析生产实现代码；测试仅观察交付 ZIP 的弹窗 DOM 与 HTTP 请求。

## Agent 交接

- 任务编号：EXT-ROUTE-003
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：功能实现 Agent
- 已完成内容与产物：`tests/e2e/ext_route_003.spec.ts`、`tests/e2e/playwright.ext_route_003.config.ts` 与本报告。
- 接收方工作范围：插件生产实现、交付 ZIP 与实现说明；测试目录、断言和门槛只读。
- 输入文档：`docs/tasks/EXT-ROUTE-003.md`、本报告。
- 建议命令：在根目录运行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_003.config.ts --reporter=line`，再跑 EXT-ROUTE-002 与 EXT-ROUTE-001 回归。
- 结果或风险：目标功能缺失稳定 RED，旧插件保存与 URL/hash 回归均通过。
- 本阶段完成条件：实现交 `READY_FOR_TEST` 后由测试 Agent 独立复测。
