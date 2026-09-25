# WEB-CAL-001 实现说明

- 状态：`READY_FOR_TEST`
- 修改范围：`frontend/src/router/index.ts`、`frontend/src/views/ApplicationsView.vue`、`frontend/src/views/CalendarView.vue`、`frontend/src/api/calendar.ts`
- 已实现行为：为登录用户注册受保护的 `/calendar` 路由，并从投递导航抽屉提供“日历”入口。页面默认定位北京时间今天所在自然月，展示该月覆盖的完整周；支持周/月切换、前后周期和回到今天。每次视图变化调用 `GET /api/v1/calendar/events/` 请求完整日期窗口，走统一认证客户端。事件按北京时间日期裁成每日片段，00:00～24:00 纵向定位，长度按当日交集时长计算；午夜结束采用左闭右开边界。周视图显示跨日续接，重叠事件分别保留键盘可操作入口；月格压缩事件文字，拥挤日期可展开全部安排。笔试使用文字、符号和边框样式与面试区分。事件详情显示公司、岗位、阶段、完整起止、时长及北京时间，并链接原投递编辑页。空日、加载中、API 错误及重试均有明确界面；请求序号保证仅最新范围响应生效，认证失败沿用现有 HTTP 刷新/退出处理。
- 数据库迁移：无。
- 配置变化：无；未新增运行时依赖。
- 已知限制：日历按固定 `Asia/Shanghai`（UTC+08:00）解释和显示事件；月份日期格在窄屏下可横向滚动，以保留 7 列和紧凑时间轴。
- 环境：Windows；项目 `.nvmrc` 为 `20.19.0`；实际使用 nvm 安装目录中的 Node.js `v20.19.0` 与 npm `10.8.2`。`nvm install 20.19.0` 的远程校验和刷新返回 nodejs.org EOF；本机已有该版本，复核其直接可执行文件版本后继续运行脚本。npm 依赖与锁文件未变更。
- 自检结果：`npm run test -- tests/test_web_cal_001.spec.ts --reporter=dot`：1 个测试文件、11 项通过；路由注册使原先有条件跳过的 10 项 UI 用例均已运行。`npm run lint` 通过；`npm run build` 通过（Vite 输出现有 CommonJS 配置兼容性提示）。以上为实现 Agent 自检，不能替代测试 Agent 独立复测。
- 建议复测命令：在 `frontend/` 使用 nvm 选择 `.nvmrc` 版本后，运行 `npm run test -- tests/test_web_cal_001.spec.ts --reporter=dot`。
- 测试完整性声明：未修改测试、断言、跳过条件或质量门槛。

## Agent 交接

- 任务编号：`WEB-CAL-001`
- 当前状态：`READY_FOR_TEST`（任务单状态由项目管理 Agent 更新）
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：新增受保护日历路由、投递导航入口、日历查询 API 客户端与周/月视图；本说明记录契约和自检结果。
- 接收方工作范围：依据 `docs/tasks/WEB-CAL-001.md`、CAL-001 第 4 节、CAL-002 公开 API 契约及 `docs/test-reports/WEB-CAL-001-red.md` 独立复测，不修改生产实现。
- 输入文档：`docs/tasks/WEB-CAL-001.md`、`docs/requirements/CAL-001.md`、`docs/test-reports/WEB-CAL-001-red.md`、`docs/test-reports/CAL-002-passed.md`、`docs/tasks/APP-008.md`、`docs/test-reports/APP-008-passed.md`、`docs/tasks/WEB-APP-005.md`、`docs/implementation-notes/WEB-APP-005.md`。
- 建议命令：`npm run test -- tests/test_web_cal_001.spec.ts --reporter=dot`。
- 结果或风险：日历专项全部 11 项通过；Vue/TypeScript lint 与生产构建通过。远程 nvm 校验和查询失败，但本机项目指定运行时已存在并经直接检查确认。
- 本阶段完成条件：由原测试 Agent 完成独立专项复测并提交 `TEST_PASSED` 或 `TEST_FAILED` 报告。
