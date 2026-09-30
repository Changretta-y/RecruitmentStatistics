# WEB-APP-006 TEST_PASSED

- 测试角色：独立测试 Agent（release_tests）。
- 环境：Windows，Node 20.19.0、npm 10.8.2；本机 Edge + Vite 127.0.0.1:5189；隔离合成数据库的真实 API 127.0.0.1:8019。真实集成只注册合成用户，不访问生产账号或数据。
- 命令与结果：在 `frontend/` 执行 `npm run test:sharing -- --config=tests/playwright.web_app_006.config.mts --reporter=json`，12/12 通过、0 unexpected、0 flaky；其中真实 API + Edge 集成在最终 375px 截图调整后单独重跑 1/1 通过。HTTP fixture 覆盖其余 11 项。受影响旧 `WEB-APP-003/005` 单测 19/19、`WEB-APP-002/004` 单测在独立复测中 15/15 通过；`npm run lint` 与 `npm run build` 均退出 0。
- 公开输入：公司嵌套对象、两个岗位各自的投递链接和备注、公司共享 AI 面/测评/笔试各一组、同一岗位两次同名面试；真实 API 路径执行合成用户注册、登录、创建、公开 GET、浏览器刷新、局部编辑与子资源删除。
- 期望行为：多岗位新增/编辑/删除互不覆盖，shared stages 唯一，重复面试保留；刷新后仍可展开岗位并用键盘操作；PATCH 只携实际修改对象 selector ID，未改 URL/旧 ID 在最终 GET 中保留，子删除只影响目标；保存失败保留输入、服务端新 ID 和剩余删除队列，重试不重复创建；375px 页面与编辑器完整可读且无横向溢出。
- 实际行为：上述目标套件均通过。真实 GET 验证创建后两个岗位和共享流程持久化；局部保存与删除后未编辑岗位的链接/ID 保留、修改和删除仅落在指定对象。HTTP fixture 验证 PATCH 成功后 DELETE 首次 503、再次重试时不重复新增岗位/面试；网络失败和未保存确认等公开交互通过。
- 是否稳定复现：最终 Edge 完整 12/12；真实 API/375px 最终单项 1/1。桌面与375px展开、编辑截图均已目视检查；375px重新载入后 `innerWidth`、document/body `scrollWidth` 均为 375，主内容宽于 300，导航默认折叠，两岗位卡片和共享测评可完整阅读。
- 截图证据：桌面展开 `G:\job\docs\test-reports\WEB-APP-006-qa-desktop-expanded.png`、375px展开 `G:\job\docs\test-reports\WEB-APP-006-qa-mobile-expanded.png`、桌面编辑 `G:\job\docs\test-reports\WEB-APP-006-qa-desktop-edit.png`、375px编辑 `G:\job\docs\test-reports\WEB-APP-006-qa-mobile-edit.png`。375px展开图精确 375×1910，顶部导航在页顶且无侧栏残片。
- 完整前端回归：原样 `npm run test` 为 **87/90 通过**，3 项默认 5 秒超时，分别是 `WEB-AUTH-002` 用户恢复、`WEB-APP-002` 首个列表渲染、`WEB-APP-004` 首个删除确认；均无业务断言失败。三个超时项各自以默认 5 秒单项定向重跑均通过，002/004 合跑使用 CLI `--testTimeout=15000` 为 15/15 通过，测试文件及业务断言门槛未因此改动。完整并行套件的冷启动性能仍不稳定，不能宣称全项目单测全绿。历史认证 logout/coverage 基线也不属于本任务通过范围。
- 覆盖的验收标准：任务单的多岗位表单与列表展开、共享流程、重复面试、嵌套 API 持久化、局部变更和子删除、部分保存失败重试、键盘与无写展开、失败/未保存处理、搜索分页排序及旧列表/删除/表单时长回归、桌面与375px可读性。
- 未覆盖风险：完整前端套件在当前机器默认 5 秒超时下的并行首载波动需后续专门处理；本报告的真实 API 验证限隔离合成环境，不代表生产环境验收。
- 黑盒声明：未读取或分析 `frontend/src`、`backend/apps` 或其他生产实现；只依据任务公开契约、HTTP 响应、可见 UI 和测试配置进行独立复测。

## Agent 交接

- 任务编号：WEB-APP-006。
- 当前状态：TEST_PASSED（目标套件）；完整前端单测 87/90 的超时如上单独披露。
- 发送角色：测试 Agent；接收角色：项目管理 Agent。
- 已完成内容与产物：最终真实集成测试、独立复测结果、本报告及四张截图。
- 接收方工作范围：按任务单做独立验收与状态结论。
