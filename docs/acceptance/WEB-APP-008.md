# WEB-APP-008 验收记录

- 状态：`ACCEPTED`
- 验收角色：项目管理 Agent
- 验收时间：2026-10-07（Asia/Shanghai）
- 任务单：`docs/tasks/WEB-APP-008.md`
- 需求契约：`docs/requirements/WEB-APP-008.md`
- RED 报告：`docs/test-reports/WEB-APP-008-red.md`
- 测试通过报告：`docs/test-reports/WEB-APP-008-passed.md`
- 实现说明：`docs/implementation-notes/WEB-APP-008.md`
- 验收依据：`docs/agents/project-manager.md`、`docs/agents/workflow.md`、`docs/agents/templates.md` 及系统设计第 8、9、11、12 节。
- 验收方式：核对任务契约、TDD 状态和测试 Agent 提供的独立公开 HTTP/UI 证据；未将实现 Agent 自检替代独立复测。

## 交付物与流程门禁

- [x] 需求契约和任务单存在，范围、公开 API/UI 行为、错误行为及验收标准已定义。
- [x] `RED_CONFIRMED` 证据存在；失败来自缺失公开行为而非测试基础设施错误。
- [x] 实现说明存在并标注 `READY_FOR_TEST`，记录了生产修改范围。
- [x] 最新独立测试报告标注 `TEST_PASSED`：后端 `15/15`、前端 `3/3`，两条指定命令退出码均为 `0`。
- [x] 项目管理 Agent 已逐条核对公开验收标准，任务单状态更新为 `DONE`。

## 标准与证据

- [x] 公司建议主流程：建议复用认证应用列表，按 `page_size=100` 跨全部页面读取；公开证据覆盖当前用户隔离、首尾空白/大小写去重、空输入和选中公司后的搜索。
- [x] 建议选择查询状态：选择后填入规范公司名、关闭 listbox、只执行一次 `page=1` 普通搜索，并保留 `page_size`、状态、日期和排序条件；无写请求且不替换主列表。
- [x] 建议异常与缓存隔离：空列表、无匹配、`401`、`500`/网络错误和重试入口均有独立前端证据；建议 `401` 不触发全局登录跳转，错误不阻断手工搜索；实现交接记录认证用户变化清除缓存。
- [x] 默认拒绝末位排序完整性：服务端分页前按拒绝分组排序，非拒绝优先、完全拒绝末位；多岗位混合状态保持非拒绝；相同 `updated_at` 使用 `id DESC` 稳定裁决。
- [x] 显式合法非默认排序：独立 API 黑盒复测证明自定义合法 `ordering` 不额外强制拒绝公司末位。
- [x] 既有查询与权限回归：报告覆盖搜索、状态/current_stage、日期筛选、排序、`page_size`、未认证 `401`、当前用户隔离和建议不调用共享/公共接口；当前任务未修改共享授权契约。
- [x] 页码 UI 完整性：提供 `1..total_pages` 选择器和输入跳转；合法跳转保留查询状态；首末页、无数据、外部 URL 超页规范化及非法输入不发请求均有公开证据。
- [x] API 分页边界：超页返回 `200` 空结果；非法 `page` 返回字段级 `400 VALIDATION_ERROR`；分页链接保留 `page_size`、搜索、状态、日期和排序参数。
- [x] 时区查询状态：实现说明记录翻页和超页规范化保留带时区日期筛选值，独立前端专项通过。
- [x] TDD 阶段顺序：`RED_CONFIRMED` → `READY_FOR_TEST` → `TEST_PASSED` → 本次项目管理验收，符合工作流门禁。

## 非阻塞说明

- 最新报告未运行 WEB-APP-006 真实隔离 API 全量回归及无关全量套件；报告已将其标为相邻回归/环境范围，不影响本任务指定的 WEB-APP-008 独立验收命令，故不构成本任务阻塞。
- Vite `configLoader: 'native'` 与 Vue Router `next()` 仅为既有警告，未导致专项测试失败。

## 结论

- 结果：通过，`ACCEPTED`。
- 退回角色：无。
- 阻塞原因：无。
- 后续动作：任务单状态置为 `DONE`；如需 WEB-APP-006 或全量回归，另行按对应任务流程执行。
