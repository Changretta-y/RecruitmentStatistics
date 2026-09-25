# WEB-CAL-001 TEST_PASSED

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 工作目录：`G:\job\frontend`
- 环境：Windows；Node.js `v20.19.0`（`.nvmrc`）；npm `10.8.2`；Vitest `4.1.11`
- 依赖同步：实现未修改依赖或锁文件；复用 RED 阶段按 `frontend/package-lock.json` 安装的依赖。每次运行前执行 `nvm use 20.19.0`，复核该 nvm 版本的 Node 可执行文件为 `v20.19.0`，并通过它运行 npm CLI。
- 实现代码：未读取或修改 `frontend/src/`。

## WEB-CAL-001 专项复测

命令（在 `frontend/`）：

```text
npm run test -- tests/test_web_cal_001.spec.ts --reporter=dot
```

结果：`Test Files 1 passed (1)`、`Tests 11 passed (11)`。模块加载时确认 `/calendar` 路由已注册，因此 10 项 UI 用例均已启用，没有跳过。

公开行为覆盖包括：

- 已登录用户可从投递页面导航到受保护的 `/calendar`；未登录用户按原路由保护跳转到登录页。
- 默认请求今天所在月份覆盖的完整周（周一开始）；周/月切换、前后翻页和回到今天均请求预期的左闭右开日期范围，并显示“北京时间”及 `Asia/Shanghai`。
- 周/月视图按纵向 00:00～24:00 排列；上午、下午事件的位置及事件长度符合开始时刻和时长的比例；月视图日期格保留紧凑时间轴。
- 重叠笔试和面试分别可访问；展示时间与时长，详情显示公司、岗位、阶段、原始起止和时长，并提供原投递编辑入口。
- 跨午夜安排在相交日期显示续接片段；恰好午夜结束的安排不进入次日；键盘可打开事件详情。
- 拥挤日期可展开查看全部安排，笔试与面试有非颜色区分；无安排和 API 错误状态明确，失败后可重试。
- 快速切换只采用最新范围响应。

## 相邻回归

认证路由专项：

```text
npm run test -- tests/test_web_auth_002.spec.ts --reporter=dot
```

结果：`Test Files 1 passed (1)`、`Tests 9 passed (9)`。受保护页面、redirect、登录态和退出相关路由行为通过。

另将日历专项、认证路由及 `WEB-APP-002` 页面测试单 worker 合跑：

```text
npm run test -- tests/test_web_cal_001.spec.ts tests/test_web_app_002.spec.ts tests/test_web_auth_002.spec.ts --reporter=dot --maxWorkers=1
```

结果：`Tests 25 passed, 2 failed (27)`。日历 11 项和认证 9 项均通过；`WEB-APP-002` 的两项失败是既有投递列表问题：浏览器后退后搜索框未恢复 URL 条件，以及退出后当前路由仍停留在 `/applications`。这两项相同失败已记录在先前的 `docs/test-reports/WEB-APP-005-passed.md` 全量前端回归报告中，未发现与日历路由或导航入口相关的新失败。`WEB-APP-002` 另 5 项通过。

## 结论与交接

日历专项 11/11 和认证路由相邻回归 9/9 通过；原先 10 项因日历路由缺失而跳过的 UI 用例现已全部激活并通过。混合运行中暴露的两个列表失败与先前报告完全相同，属于既有 WEB-APP-002 回归问题。

- 通过 / 失败：日历专项 `11 / 0`；认证回归 `9 / 0`；包含 WEB-APP-002 的合跑 `25 / 2`。
- 稳定性：独立专项和认证任务定向运行均全部通过；合跑的两项列表失败与先前记录一致。
- 未覆盖风险：本次使用 jsdom 和公开 DOM/可访问性入口验证时间轴坐标比例，没有启动真实浏览器核验不同视口下的像素布局；实现说明记录月视图窄屏可横向滚动。
- 黑盒声明：依据任务单、需求和公开 API/UI 行为运行既有测试；未通过文件查看、搜索或分析生产实现内容，未修改测试或断言。结束时误执行了一次未限定路径的 `git diff --check`；它只输出其他工作文件的行尾提示，没有输出或人工检查生产源代码内容。后续未再对生产目录执行任何命令。

## Agent 交接

- 任务编号：`WEB-CAL-001`
- 当前状态：`TEST_PASSED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent
- 已完成内容与产物：专项测试 `frontend/tests/test_web_cal_001.spec.ts`；RED 报告 `docs/test-reports/WEB-CAL-001-red.md`；独立通过报告 `docs/test-reports/WEB-CAL-001-passed.md`。
- 接收方工作范围：依据 WEB-CAL-001 验收标准审核本通过报告和实现说明，并按工作流记录验收结论。
- 输入文档：`docs/tasks/WEB-CAL-001.md`、`docs/requirements/CAL-001.md` 第 3、4 节、`docs/implementation-notes/WEB-CAL-001.md`、`docs/test-reports/WEB-CAL-001-red.md`、`docs/test-reports/WEB-CAL-001-passed.md`。
- 建议命令：在 `frontend/` 使用 `.nvmrc` 指定的 Node.js 版本执行本报告中的专项命令。
- 结果或风险：日历专项与认证相邻回归通过。WEB-APP-002 既有的 2 项 URL/退出交互失败已由先前报告记录。
- 本阶段完成条件：已满足；交项目管理 Agent 验收。
