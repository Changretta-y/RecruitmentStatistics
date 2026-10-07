# WEB-APP-008 TEST_FAILED

- 测试角色：测试 Agent
- 状态：`TEST_FAILED`
- 环境：Windows；Python 3.11.13；uv；Node.js 20.19.0（nvm）；npm 10.8.2；PostgreSQL 隔离测试环境；Playwright Desktop Edge
- 命令：
  - `backend/tests/run-isolated-postgres.ps1 -PytestArguments @('tests/test_web_app_008_api.py','--tb=no','-q')`
  - `frontend/node_modules/.bin/playwright.cmd test --config=tests/playwright.web_app_008.config.mts --reporter=line`
- 后端通过 / 失败：`15 / 0`
- 前端通过 / 失败：`2 / 1`

## 新增测试

- `backend/tests/test_web_app_008_api.py`
  - 相同 `updated_at` 的公开列表响应按 `id DESC` 排序。
  - 未认证列表 `401`。
  - 另一用户不可见当前用户记录。
  - `search`、`application_status`、日期范围和 `page_size` 请求/响应断言。
  - 空数据 `200`、`total_pages=0`、空 `results`。
  - `page=999` 返回 `200`、空 `results` 和真实分页元数据。
- `frontend/tests/test_web_app_008.e2e.spec.ts`
  - 新增一个综合测试，覆盖建议 API 的 `[]`、`401`、`500`，以及首末页、空列表控件、超页 URL 规范化和查询参数保留。

## 失败证据

- 公开输入：建议响应为 `[]`、`401` 或 `500` 的 route fixture；登录后聚焦关键字输入框。
- 期望：建议面板可观察，分别显示空状态、无匹配或失败/重试提示，且不显示公共公司；随后完成分页边界和 URL 参数断言。
- 实际：新增综合 Playwright 测试在 `getByRole('listbox').toBeVisible()` 处失败，4 秒内未找到可见 `listbox`；因此该测试的建议状态断言及后续分页边界断言尚未执行。
- 失败位置：`frontend/tests/test_web_app_008.e2e.spec.ts:127`。
- 稳定性：本次运行复现 1 次；按用户要求未继续重跑或进行长回归，稳定性待实现修复后由测试 Agent 独立复测。

## 回归结果

- 既有 WEB-APP-008 Playwright 测试：`2 passed / 0 failed`。
- 本次新增后端测试已全部通过。
- 未运行全量测试，也未修改生产代码。

## 覆盖的验收标准

- 后端 tie-break、认证、用户隔离、查询参数、空数据和 API 超页边界已有通过证据。
- 前端新增建议异常、首末页、无数据、外部超页规范化及全部查询参数保留的测试已写入，但因建议 `listbox` 未出现，尚无通过证据。

## 交接

- 当前状态：`TEST_FAILED`
- 退回角色：功能实现 Agent
- 原因：新增公开 UI 场景在建议 API 返回异常/空结果后未呈现可观察 `listbox`，导致新增综合测试无法继续验证后续边界行为。
- 后续动作：实现修复后，由测试 Agent 使用同一命令独立复测；本报告不宣称 `TEST_PASSED`。

## 黑盒声明

测试仅观察公开 HTTP route、URL 和 DOM/可访问角色；未读取或分析 `backend/apps/`、`frontend/src/`，未修改生产代码。
