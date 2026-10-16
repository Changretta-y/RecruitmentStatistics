# WEB-APP-014 提示词管理页面

- 状态：DONE
- 用户价值：在独立页面集中管理自己的提示词，点击即可复制，减少重复输入。
- 范围：新增受保护的 `/prompts` 页面、主导航入口、搜索、预设展示、新增/编辑/删除和复制交互。
- 非范围：手机端专项适配、公共共享、AI 执行提示词。
- 依赖：APP-014 提供提示词 API；现有 AppShell、认证和 Vuetify 组件库。
- 允许修改范围：项目管理仅 `docs/tasks/`、`docs/acceptance/`；测试仅 `frontend/tests/`、`tests/e2e/`、`docs/test-reports/`；实现仅 `frontend/src/`、`docs/implementation-notes/`。

## 公开 UI 契约

- 主导航出现“提示词管理”，进入 `/prompts`；未登录访问重定向到登录页。
- 页面展示搜索框和提示词卡片/列表；每项显示标题、内容、预设标识以及“复制、编辑、删除”操作。
- 点击“复制”调用浏览器剪贴板并显示成功提示；剪贴板不可用时显示错误提示，不删除或修改记录。
- 点击“新增提示词”打开表单，标题和内容必填；编辑复用表单，保存后刷新当前列表。
- 删除需二次确认，成功后从列表移除；取消不产生请求。
- 搜索只影响当前用户的提示词，空结果显示明确状态；加载和 API 错误有可见提示。
- 页面沿用现有 Vuetify 组件和 AppShell 桌面风格。

## 验收标准

- [ ] 路由、导航和登录保护可观察。
- [ ] 预设提示词展示、搜索、复制、新增、编辑、删除流程可完成。
- [ ] 表单校验和网络错误有可见反馈，操作不会串用户。
- [ ] 现有投递、日历、通知页面回归通过。

## RED 证据

- 测试提交：`ab747bb`
- 报告：`docs/test-reports/WEB-APP-014-red.md`
- 结果：后端 5 failed/0 errors，前端 8 failed/0 passed；均为缺失提示词 API/页面行为导致，专用 PostgreSQL 与 Playwright 环境正常。

## Agent 交接

- 当前状态：READY_FOR_TEST → TEST_PASSED → ACCEPTING → DONE。
- 测试 Agent：`company_tests`，已提交黑盒测试。
- 实现提交：`d3fed17`
- 实现说明：`docs/implementation-notes/APP-014.md`、`docs/implementation-notes/WEB-APP-014.md`
- 实现 Agent：`company_implementation`，负责后端模型/API、迁移及前端页面/路由/导航。

## TEST_PASSED 证据

- 测试提交：`3cf56bd`（测试夹具修正）、`f5fe326`（通过报告）
- 报告：`docs/test-reports/WEB-APP-014-passed.md`
- 结果：专项通过，现有认证/投递和公司页面回归通过；另有历史 WEB-APP-011 断言问题与本任务无关。
