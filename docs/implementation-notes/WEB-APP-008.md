# WEB-APP-008 实现说明

- 状态：`READY_FOR_TEST`
- 修改范围：`backend/apps/applications/views.py`、`frontend/src/api/http.ts`、`frontend/src/api/applications.ts`、`frontend/src/components/AppShell.vue`、`frontend/src/views/ApplicationsView.vue`
- 已实现行为：
  - 应用列表在缺省排序或 `ordering=-updated_at` 时，先按公司全部公开岗位的有效 `current_stage` 计算拒绝分组，再按非拒绝优先、`updated_at DESC`、`id DESC` 排序后分页；多岗位只有全部岗位拒绝才进入末位分组，显式其他合法排序保持原语义。
  - 前端复用认证应用列表接口，以 `page_size=100` 跨 `total_pages` 读取建议数据；建议请求不携带主列表搜索、状态、日期或排序参数，独立维护加载/错误/缓存状态，按去首尾空白且不区分大小写去重并保留首次展示名。
  - 公司建议面板支持 focus/click 打开、包含匹配、listbox/option 语义、空结果和失败重试；空列表、无匹配、401 和网络/服务错误均保留可见 listbox，401 不触发全局刷新跳转，错误状态提供重试入口且不回退公共查询。401 或认证用户变化会清空建议缓存，建议读取不会替换主列表、URL 或主列表加载状态。
  - 选择建议会填入规范公司名、关闭面板并执行一次 `page=1` 的普通搜索，同时保留 page_size、状态、日期和排序查询状态；手工输入、Enter 和查询按钮继续沿用原搜索流程。
  - 主列表增加 `1..total_pages` 原生可访问页码选择器和正整数页码输入；非法、越界、非安全整数输入只显示错误且不发请求。外部 URL 越界在响应后规范化到最后有效页，无数据规范化到第 1 页。翻页和超页规范化保留带时区的日期筛选查询值，不将其意外转换为 UTC。侧栏导航显式标记为 navigation，避免与建议 listbox 产生重复无障碍角色。
- 数据库迁移：无。
- 配置变化：无运行时配置或依赖变化。
- 已知限制：本轮未替代测试 Agent 的独立复测；实现完成后仍需由测试 Agent 按任务流程提交 `TEST_PASSED`。前端已有 Vite 配置会输出 `configLoader: 'native'` 兼容性警告，不影响本任务构建结果。
- 自检结果：
  - 环境：Python `3.11.13`、uv `0.7.21`、Node.js `20.19.0`、npm `11.5.2`（nvm 切换后）；按 `.nvmrc` 和 `.python-version` 执行。
  - `backend/tests/run-isolated-postgres.ps1 -PytestArguments @('tests/test_web_app_008_api.py','--tb=short','-q')`：`7 passed`。
  - `frontend` 中 `npm run lint`：通过；`npm run build`：通过。
  - `frontend` 中 `node_modules/.bin/playwright.cmd test --config=tests/playwright.web_app_008.config.mts --reporter=line`：`3 passed`（含建议空列表、401、500、错误重试入口以及分页边界/查询状态保留）。
  - 回流后 `backend` 中 `uv run ruff check .`：通过。
  - 回流后 `frontend` 中 `npm run lint`：通过；`npm run build`：通过。
- 建议复测命令：
  - 后端：`& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_web_app_008_api.py','--tb=no','-q')`
  - 前端：`Set-Location frontend; .\node_modules\.bin\playwright.cmd test --config=tests/playwright.web_app_008.config.mts --reporter=line`
- 测试完整性声明：未修改测试、断言或质量门槛；测试目录和既有测试报告保持只读。

## Agent 交接

- 任务编号：`WEB-APP-008`
- 当前状态：`READY_FOR_TEST`
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：生产实现及本实现说明；后端排序、前端建议和分页专项自检通过。
- 接收方工作范围：仅依据公开 HTTP/UI 契约独立复测，不修改生产实现；重点复核建议用户隔离/401/失败重试、默认排序跨页、多岗位混合状态、显式排序和所有页码边界。
- 输入文档：`docs/tasks/WEB-APP-008.md`、`docs/requirements/WEB-APP-008.md`、`docs/test-reports/WEB-APP-008-red.md`、APP-009/APP-010/APP-011 公开契约。
- 本阶段完成条件：测试 Agent 独立复测并提交 `TEST_PASSED` 或可复现的 `TEST_FAILED` 报告；功能实现 Agent 不设置 `TEST_PASSED` 或 `DONE`。
