# WEB-APP-008 TEST_PASSED

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 回流结论：本次补充黑盒 API 测试已完成并通过；可交项目管理 Agent 继续验收，尚不据此直接设置 `DONE`。
- 环境：Windows；Python 3.11.13；uv 0.7.21；Node.js 20.19.0（nvm）；npm 10.8.2（实际运行版本）；PostgreSQL 隔离测试环境；Playwright Desktop Edge
- 命令：
  - `backend/tests/run-isolated-postgres.ps1 -PytestArguments @('tests/test_web_app_008_api.py','--tb=no','-q')`
  - `frontend/node_modules/.bin/playwright.cmd test --config=tests/playwright.web_app_008.config.mts --reporter=line`
- 最新独立复测通过 / 失败：后端 `15 / 0`（17.71s）；前端 `3 / 0`（14.4s）；两条命令退出码均为 0。

## 2026-10-07 最新独立复测

- 后端指定命令：`15 passed in 17.71s`。
- 前端指定命令：`3 passed (14.4s)`。
- 后端 15 项覆盖默认拒绝末位排序、相同 `updated_at` 的 `id DESC` 稳定排序、多岗位混合状态、显式排序、认证与用户隔离、搜索/状态/日期/page_size 查询、空数据、超页 `200` 空结果、分页链接参数保留，以及非法 `page` 的字段级 `400 VALIDATION_ERROR`。
- 前端 3 项覆盖认证用户建议跨页读取与公司名去重/选择、建议空列表/401/500 与错误重试隔离、页码首末边界/无数据/超页 URL 规范化、非法页码不发请求，以及 page_size、搜索、状态、日期和排序参数保留。
- 前端仅输出既有 Vite `configLoader: 'native'` 兼容性警告和 Vue Router `next()` 弃用警告，未导致测试失败。

## 专项公开证据

- 后端默认列表按公开 `current_stage` 将非拒绝公司置于完全拒绝公司之前；多岗位公司只要存在一个非拒绝岗位即保持在非拒绝分组。
- 后端 `page=0`、负数、非整数、小数、空值和空白值均返回字段级 `400 VALIDATION_ERROR`，详情指向 `page`。
- 前端聚焦关键字框后，建议从认证应用列表跨页读取，按首尾空白和大小写去重；选择建议后执行 `page=1` 搜索，并保留 `page_size`、状态、日期和排序条件。
- 前端页码选择器提供 `1..total_pages`；合法页码跳转保留查询条件；非法页码显示错误且不发起列表请求。

## 历史相邻回归（不属于本轮）

- APP-011 后端：`24 passed / 0 failed`。
- WEB-APP-007 前端：`5 passed / 0 failed`。
- WEB-APP-006 前端：`11 passed / 1 failed`。失败项为 `test_web_app_006_real.e2e.spec.ts`，公开错误为连接 `127.0.0.1:8019` 被拒绝；该隔离后端未启动，属于环境阻塞，未作为 WEB-APP-008 专项失败依据。
- 按用户要求已停止继续回归，未运行全量长回归；WEB-APP-006 的真实隔离 API 场景及全量套件未覆盖。

## 覆盖的验收标准

- 公司建议的当前用户来源、跨页读取、去重、选择搜索及查询状态保持。
- 默认拒绝末位排序、多岗位混合状态判断和服务端分页前排序。
- 页码选择、数字输入、查询状态保持及非法输入不发请求。
- 非法 API 页码的字段级错误行为。

## 未覆盖风险

- 未运行 WEB-APP-006 真实隔离 API 回归、无关全量套件或全浏览器矩阵；这些不在本轮用户指定命令范围内。
- 历史失败报告 `WEB-APP-008-failed.md` 保留作为回流记录；本报告中的最新专项结果已覆盖其前端 `listbox` 阻塞场景。

## 黑盒声明

测试仅依据公开 HTTP 请求/响应、URL 和可观察 UI/DOM 行为进行；未读取、搜索、枚举或分析 `frontend/src/`、`backend/apps/`，未修改生产代码、既有断言或质量门槛。
