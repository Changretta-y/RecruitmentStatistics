# WEB-APP-006 RED_CONFIRMED（核心 UI 先行）

- 测试角色：release_tests，原独立测试角色。
- 依赖门禁：APP-009 已 DONE，PM 于 9e29916 正式交接 TEST_WRITING 后编写本套件。
- 环境：Windows；nvm 当前 Node 20.19.0（与 .nvmrc、engines 一致），npm 10.8.2；`npm ci` 按 frontend/package-lock.json 成功；项目 Playwright 与已安装 Edge，Vite 127.0.0.1:5189。锁定依赖 abbrev/nopt 对 Node 的既有 engine 警告不影响本次运行，不修改运行时或锁文件。
- 命令：在 frontend 下 `npm run test:sharing -- --config=tests/playwright.web_app_006.config.mts`。末尾 config 覆盖既有 sharing config，仅执行本任务先行套件。
- 通过 / 失败：1 / 3，退出码 1。基线真实 Edge 通过登录、列表 GET、公司行渲染与新增页打开，排除浏览器、Vite、fixture、路由与表单环境问题。
- 公开输入：HTTP 公共嵌套公司对象，两个岗位各有独立链接/备注与两条同名面试，公司级 AI 面/测评/笔试各一个；同时保留 APP-009 兼容 flat 投影。合成认证，不访问生产账号。
- 期望行为：新增页可添加第二岗位、独立编辑；有唯一测评时间入口，增加岗位不复制共享入口；多岗公司行可通过 keyboard 展开/折叠，aria-expanded 正确、展示两个岗位与测评且不发写请求。
- 实际行为：新增页没有“添加岗位/新增岗位”按钮；测评时间公开可见输入数量 0（期望 1）；存在的多岗位公司行没有 aria-expanded 展开按钮（期望 1）。三项均在已通过基线的公开 UI 上因缺失新需求而失败。
- 是否稳定复现：三个缺失行为每次加载可观察；最终完整隔离运行固定 1/3。开发中旧历史入口文案选择器与并行试跑共享 Vite 生命周期造成的测试/环境失败已修正且排除，不计入有效 RED。
- 回归结果：本阶段只确认核心 RED 与 UI/HTTP 夹具基线；尚未运行旧列表、表单、时长、认证或完整前端回归。既有 REL-001 auth-store 3 条 logout 路由与 coverage 基线按 PM 说明保留，不能用本次结果声称全项目通过。
- 覆盖的验收标准：核心岗位添加、唯一共享测评入口、多岗公司键盘展开与无写请求的先行断言。
- 待补测试：完整 nested POST/PATCH 与刷新、岗位 application_url 独立保留、岗位/面试子 DELETE、共享日期 null/时长联动、失败完整输入保留/重试/重复提交/未保存确认、PATCH 成功后 DELETE 503 部分完成与 ID 采纳/不重复新增、删除确认岗位数、分页搜索筛选排序及单岗位回归；真实 8019 后端 + Edge 合成用户持久集成和桌面/375px 截图 QA。补充测试继续独立提交且不读取生产实现。
- 黑盒声明：未读取或分析 frontend/src 或后端生产实现；仅使用公开 HTTP 与可见 DOM/无障碍交互。测试代码无生产 imports；输出出现实现路径时不沿路径读取或调查。当前 HTTP fixture RED 不宣称后端持久集成已通过。

## Agent 交接

- 任务编号：WEB-APP-006。
- 当前状态：RED_CONFIRMED（核心公开 UI 门禁已满足）。
- 发送角色：release_tests。
- 接收角色：PM，再交 company_implementation。
- 产物：frontend/tests/playwright.web_app_006.config.mts、frontend/tests/test_web_app_006.e2e.spec.ts、测试产物忽略规则、本报告。
- 实现范围：按任务单仅修改 frontend/src 与实现说明；测试只读。
- 测试后续：本角色继续先行补齐剩余行为与回归，READY_FOR_TEST 后独立执行相同断言及真实集成。
