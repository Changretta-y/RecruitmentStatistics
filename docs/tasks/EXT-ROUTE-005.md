# EXT-ROUTE-005 插件入口分流与统一视觉

- 状态：DONE
- 用户价值：插件打开后先看到简洁入口，用户可选择查看投递记录或新增投递，避免所有内容一次性纵向展开。
- 范围：插件弹窗增加入口页和两个功能入口；查看投递记录与新增投递按需显示；统一按钮、卡片、颜色、圆角、间距和字体风格。
- 非范围：不改变已投递公司读取/搜索 API、不改变新增投递保存匹配、认证、URL/hash 或版本号。
- 依赖：EXT-ROUTE-003 已投递公司查看；EXT-ROUTE-004 插件 v0.2.0 交付包。
- 允许修改范围：项目管理仅 `docs/tasks/`、`docs/acceptance/`；测试仅 `tests/e2e/`、`docs/test-reports/`；实现仅 `frontend/src/browser-extension/`、生成 `artifacts/`、`docs/implementation-notes/`。

## 公开契约

1. 登录后插件默认显示入口页，只有两个主要选项：“查看投递记录”和“新增投递”。
2. 点击“查看投递记录”才显示已投递公司/岗位列表与搜索；点击“新增投递”才显示当前页面采集表单和保存预览。
3. 两个功能页面都有明确的返回入口，返回入口页不会丢失登录态；功能区域不会同时纵向展开。
4. 视觉使用与主站一致的蓝色主按钮、浅色背景、白色卡片、统一边框/圆角/间距和清晰的 hover/focus 状态；不引入无法在插件包中加载的远程依赖。
5. 未登录仍只显示登录页；退出登录清除当前功能状态并返回登录页。

## 验收标准

- [ ] 登录后默认只显示两个入口选项，弹窗高度不包含采集表单和记录列表。
- [ ] 查看投递记录和新增投递按需切换，返回入口和登录态正常。
- [ ] 既有记录列表搜索、采集保存、认证异常和 URL/hash 行为不回归。
- [ ] 可加载 ZIP 中样式与结构完整，按钮/卡片/输入控件视觉统一且无远程组件依赖。
- [ ] 测试 Agent 先提交 RED，实现 Agent READY_FOR_TEST，测试 Agent TEST_PASSED，PM 验收 DONE。

## Agent 交接

- 当前状态：PLANNED → TEST_WRITING → RED_CONFIRMED → IMPLEMENTING。
- 测试 Agent：`company_tests`，仅修改 tests/e2e/ 与报告。
- RED 证据：测试提交 `257fc8e`，报告 `docs/test-reports/EXT-ROUTE-005-red.md`；专项 7 项中 4 项稳定失败，旧记录搜索、采集保存和认证回归通过。
- 实现交接：提交 `b5f3ff1`，说明 `docs/implementation-notes/EXT-ROUTE-005.md`；双入口互斥视图、统一视觉、退出清理和异步导航保护完成，专项 7/7、EXT-ROUTE-004 3/3、Node check 通过，交回测试 Agent。

## 2026-10-09 PM 验收结果

- 状态：DONE。
- RED 报告：`docs/test-reports/EXT-ROUTE-005-red.md`，提交 `257fc8e`。
- 实现说明：`docs/implementation-notes/EXT-ROUTE-005.md`，提交 `b5f3ff1`。
- 独立通过报告：`docs/test-reports/EXT-ROUTE-005-passed.md`，提交 `5e160ec`。
- [x] 登录后默认只有“查看投递记录”“新增投递”两个入口。
- [x] 两个功能按需互斥显示，可返回入口并保留登录态，退出后清理。
- [x] 记录搜索、采集预览/POST、认证和 v0.2.0 版本回归通过；专项合计 10/10。
- [x] 视觉使用本地 CSS 的主站蓝色、白卡片、边框圆角、hover/focus 状态，无远程依赖。

结论：入口分流和统一视觉契约满足，项目管理 Agent 设置 EXT-ROUTE-005 为 DONE。
