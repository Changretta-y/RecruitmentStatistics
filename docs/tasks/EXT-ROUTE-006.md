# EXT-ROUTE-006 插件顶部双按钮默认新增投递

- 状态：READY_FOR_TEST
- 用户价值：打开插件即可直接新增投递，同时可用顶部按钮快速切换查看记录，减少返回入口和额外操作。
- 范围：调整插件登录后的导航栏和默认视图；顶部固定“查看投递记录”“新增投递”两个按钮，默认显示新增投递，移除返回入口。
- 非范围：不改变记录搜索、采集保存、认证、版本号、URL/hash 和 API 数据行为。
- 依赖：EXT-ROUTE-005 双入口页面与统一视觉。
- 允许修改范围：项目管理仅 `docs/tasks/`、`docs/acceptance/`；测试仅 `tests/e2e/`、`docs/test-reports/`；实现仅 `frontend/src/browser-extension/`、生成 `artifacts/`、`docs/implementation-notes/`。

## 公开契约

1. 登录后默认显示新增投递采集表单，不显示入口页或返回按钮。
2. 采集视图顶部固定显示“查看投递记录”和“新增投递”两个按钮；当前视图按钮有清晰选中状态。
3. 点击“查看投递记录”显示已投递公司/岗位列表；点击“新增投递”显示采集表单；两个视图互斥。
4. 切换视图不丢失登录态；已有列表搜索、刷新、采集预览/保存、退出和异常状态保持不变。
5. 延续主站统一的本地 CSS 视觉风格。

## 验收标准

- [ ] 登录后默认直接显示新增投递表单。
- [ ] 顶部始终有两个切换按钮，切换记录/新增视图无需返回操作。
- [ ] 两视图互斥、选中状态明确，已有功能回归通过。
- [ ] 新 v0.2.0 ZIP 可加载，测试 Agent 先 RED，实现 Agent READY_FOR_TEST，测试 Agent TEST_PASSED，PM 验收 DONE。

## Agent 交接

- 当前状态：PLANNED → TEST_WRITING → RED_CONFIRMED → IMPLEMENTING。
- 测试 Agent：`company_tests`，仅修改 tests/e2e/ 与报告。
- RED 证据：测试提交 `445cd04`，报告 `docs/test-reports/EXT-ROUTE-006-red.md`；新专项 5 项中 3 项稳定失败，旧 EXT-ROUTE-005 回归 7/7 通过。
- 实现交接：提交 `f3e8593`，说明 `docs/implementation-notes/EXT-ROUTE-006.md`；默认新增、顶部双按钮互斥切换、移除返回和选中态完成，006 5/5、适用回归 6/6、Node/build 通过，交回测试 Agent。
