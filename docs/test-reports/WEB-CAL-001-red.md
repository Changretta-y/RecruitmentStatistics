# WEB-CAL-001 RED_CONFIRMED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 工作目录：`G:\job`
- 环境：Windows；Node.js `v20.19.0`；npm `10.8.2`；Vitest `4.1.11`
- 依赖同步：在 `frontend/` 按 `.nvmrc` 执行 `nvm use 20.19.0`，以锁文件执行 `npm ci`，成功。运行脚本前复核 Node.js `v20.19.0`；并行版本切换期间用该 nvm 安装目录中的 Node 可执行文件启动项目 npm CLI。
- 命令：在 `frontend/` 执行 `npm run test -- tests/test_web_cal_001.spec.ts --reporter=dot`
- 通过 / 失败：`0 passed, 1 failed, 10 skipped`；同一命令连续两次稳定得到相同结果。
- 公开输入：已登录用户访问公开路由 `/calendar`。
- 期望行为：路由表应匹配受保护的 `/calendar` 页面，后续可由投递页面导航进入。
- 实际行为：Vue Router 对 `/calendar` 的匹配结果为空（`matched.length === 0`），页面路由不存在；测试以该公开路由行为失败。
- 是否稳定复现：是；两次运行均在 `/calendar must resolve to an application page` 断言处失败。Vitest、Vue 插件、jsdom、依赖安装和 Node 运行环境均正常。
- 回归结果：本阶段未运行相邻回归；没有实现可供回归。
- 覆盖的验收标准：测试文件包含路由与导航、默认月份和完整周范围、周/月切换及翻页/今天、北京时间标识、重叠与跨午夜/午夜结束、24 小时轴的纵向坐标和时长比例、月视图拥挤日期的事件入口、详情和投递编辑入口、空态/API 错误/重试、快速切换的最新响应、未登录保护、笔试与面试的非颜色区分及键盘操作断言。当前路由未注册时，上述 10 项 UI 用例被有条件跳过，以避免空 `RouterView` 造成伪失败；路由加入后会自动启用。
- 未覆盖风险：启用 UI 用例后需结合实现公开的 DOM/可访问性入口复测；jsdom 不做真实浏览器像素布局测量，时间定位通过可测量的事件纵坐标/高度比例验证。当前只证明了路由缺失这一 RED 行为。
- 黑盒声明：仅依据任务单、需求和已交付的公开 API/表单契约设计测试；未读取或分析 `frontend/src/` 生产实现代码。

## Agent 交接

- 任务编号：`WEB-CAL-001`
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：功能实现 Agent
- 已完成内容与产物：`frontend/tests/test_web_cal_001.spec.ts`；本 RED 报告 `docs/test-reports/WEB-CAL-001-red.md`。
- 接收方工作范围：仅在实现 Agent 分配的 `frontend/src/` 和 `docs/implementation-notes/` 范围内实现任务单公开契约；不修改测试、断言或质量门槛。
- 输入文档：`docs/tasks/WEB-CAL-001.md`、`docs/requirements/CAL-001.md` 第 3、4 节、`docs/test-reports/CAL-002-passed.md`、`docs/tasks/APP-008.md`、`docs/test-reports/APP-008-passed.md`、`docs/tasks/WEB-APP-005.md` 及 `docs/implementation-notes/WEB-APP-005.md`。
- 建议命令：在 `frontend/` 按 `.nvmrc` 选择 Node.js `20.19.0` 并复核版本后，运行 `npm run test -- tests/test_web_cal_001.spec.ts --reporter=dot`。
- 结果或风险：当前缺少匹配 `/calendar` 的路由，稳定 RED。10 项日历 UI 用例由路由可用性条件控制，加入路由后会开始验证完整页面行为。
- 本阶段完成条件：已满足；交功能实现 Agent 实现，完成后回到测试 Agent 独立复测。
