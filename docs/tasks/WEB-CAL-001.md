# WEB-CAL-001 周/月日历页面

- 状态：`DONE`
- 用户价值：按天内的真实时间位置查看本周、本月所有笔试和面试。
- 范围：日历路由与导航入口、周/月切换、日期翻页、24 小时纵向时间轴、事件详情、空态/错误态。
- 非范围：创建自定义事件、外部日历同步、邮件设置。
- 依赖：`CAL-002` 完成；需求 `docs/requirements/CAL-001.md` 第 3、4 节。
- 允许修改范围：项目管理 Agent 仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`；测试 Agent 仅 `frontend/tests/`、`tests/e2e/`、`docs/test-reports/`；实现 Agent 仅 `frontend/src/`、`docs/implementation-notes/`。

## 业务规则与公开契约

- 登录用户可进入 `/calendar`；未登录沿用路由保护。默认显示包含今天的月份，可切换为包含今天的周；周一为首日。
- 月视图展示自然月覆盖的完整周，日期格内有**从上到下的紧凑 00:00～24:00 时间轴**；周视图每日有较宽的同向时间轴。事件在时间轴上的位置和长度反映该日与 `[start_at,end_at)` 的交集。
- 顶部提供周/月切换、上一周期、下一周期、今天，并展示当前日期范围与“北京时间（Asia/Shanghai）”。查询当前显示的完整日期范围；快速切换时只采用最新查询结果。
- 同时段事件都可进入详情；详情展示公司、岗位、阶段、完整开始/结束、时长，并能进入原投递编辑页。跨日事件在各相交日期显示片段，并可从每个片段打开同一详情。
- 每天能分辨面试与笔试、有无安排；数量过多可折叠内容但不能丢可访问事件；事件键盘可操作且不可只靠颜色区分。

## 输入、输出与错误行为

- 输入为 `CAL-002` 日期范围 API 输出；页面不直接使用投递列表分页拼接事件。
- API 失败保留当前视图框架，显示错误和重试；无事件显示明确空态；401 沿用统一认证刷新/退出处理。

## 验收标准

- [ ] `/calendar` 可由导航进入，默认当前月；周/月切换、翻页、今天均请求正确显示范围并定位日期。
- [ ] 两种视图每天从上到下对应 00:00～24:00；月格为紧凑时间轴，上午/下午事件、长短事件位置和长度可观察正确。
- [ ] 跨午夜与重叠事件均能查看；午夜恰好结束不出现在次日；详情和编辑入口正确。
- [ ] 无安排、超过可直接显示的数量、API 错误、快速切换、未登录分别有明确且不丢事件的行为。
- [ ] 面试与笔试区别、时区标识及键盘可操作入口符合契约。

## 风险与测试边界

- 月格空间有限，以时间位置正确和所有事件可经详情访问为先；可用代表性时间坐标与交互公开行为验证，不限定 CSS 实现。
- 日历固定 `Asia/Shanghai`；已有投递表单的浏览器本地时区语义应明确展示，不能混淆。

## Agent 交接

- 任务编号：`WEB-CAL-001`
- 当前状态：`DONE`
- 发送角色：项目管理 Agent
- 接收角色：项目管理 Agent
- 已完成内容与产物：需求契约、RED 报告 `docs/test-reports/WEB-CAL-001-red.md`、实现说明 `docs/implementation-notes/WEB-CAL-001.md`、独立通过报告 `docs/test-reports/WEB-CAL-001-passed.md` 及验收记录 `docs/acceptance/WEB-CAL-001.md`。
- 接收方工作范围：本任务已完成；后续变更按新任务处理。
- 输入文档：本任务单、`docs/requirements/CAL-001.md` 第 3、4 节、`docs/test-reports/WEB-CAL-001-red.md`、`docs/test-reports/CAL-002-passed.md`、`docs/tasks/APP-008.md`、`docs/test-reports/APP-008-passed.md`、`docs/tasks/WEB-APP-005.md` 及 `docs/implementation-notes/WEB-APP-005.md`。
- 建议命令：先读取 `docs/agents/environment.md`；在 `frontend/` 按 `.nvmrc` 选择并复核 Node.js `20.19.0`，运行 `npm run test -- tests/test_web_cal_001.spec.ts --reporter=dot` 作实现自检。实现自检不能替代测试 Agent 的独立复测。
- 结果或风险：本阶段唯一已确认的 RED 是 `/calendar` 路由缺失；10 项后续 UI 行为测试通过 `it.skipIf(!calendarRouteRegisteredAtLoad)` 条件跳过。测试在模块加载时检查路由表是否含有精确路径 `/calendar`，因此实现需注册该路径并满足第一项测试的受保护路由契约；测试 Agent 独立复测时应确认该前置条件解除，10 项测试随之自动启用。该条件只用于避免未注册路由时空 `RouterView` 造成伪失败，禁止删改或放宽跳过门槛。启用后若出现新的业务失败，按测试报告定位，不将其归入本次已确认的唯一 RED。
- 本阶段完成条件：测试 Agent按环境规范复核 Node.js `20.19.0`，独立运行 `frontend/tests/test_web_cal_001.spec.ts`，确认 `/calendar` 已注册使 10 项 UI 用例全部激活；运行专项与必要回归后提交 `TEST_PASSED` 或可复现的 `TEST_FAILED` 报告，production `frontend/src/` 只读。项目管理验收记录见 `docs/acceptance/WEB-CAL-001.md`。
