# WEB-APP-008 主页面公司建议、拒绝末位排序与页码导航

- 状态：`DONE`
- 角色：项目管理 Agent=需求拆解与最终验收；测试 Agent=黑盒测试、RED 证明与独立复测；功能实现 Agent=后端列表排序与前端建议/分页实现。
- 用户价值：用户可从本人历史投递公司快速搜索；默认列表优先显示未拒绝公司；可以直接选择或输入页码定位记录。
- 范围：主页面关键字输入框历史公司建议；当前用户数据范围内的建议读取；应用列表默认拒绝末位排序；页码选择器与页码输入跳转；现有 URL/API 查询状态保留和分页边界错误处理。
- 非范围：状态八值或 `current_stage` 语义重做、共享授权、全站公司目录、共享列表建议、日历/邮件 `stage`、新增筛选/排序字段、修改 page_size 允许值、生产数据迁移。
- 依赖：`APP-009`、`APP-010`、`APP-011`、`WEB-APP-006`、`WEB-APP-007`；前端现有 `ApplicationQueryState` 与 `parseApplicationQuery/serializeApplicationQuery` 查询契约。
- 产品契约：`docs/requirements/WEB-APP-008.md`。
- 允许修改范围：项目管理 Agent 仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`；测试 Agent 仅 `backend/tests/`、`frontend/tests/`、`tests/e2e/`、`docs/test-reports/`；功能实现 Agent 仅 `backend/apps/`、`backend/config/`、`backend/manage.py`、`frontend/src/`、`docs/implementation-notes/`。本轮项目管理 Agent 不修改测试或生产代码；实现 Agent 不修改测试、需求、任务或验收门槛。

## 业务规则与公开契约

### 1. 公司建议来源与隔离

- 复用认证后的 `GET /api/v1/applications/`，从当前用户所有分页结果的公司聚合对象提取 `company_name`，按首尾空白和大小写归一键去重，按接口默认最近更新顺序保留首次展示名。
- 建议请求不带主列表的 `search`、`application_status`、日期筛选；从 `page=1&page_size=100` 读取到 `total_pages`。建议请求维护独立状态，不覆盖主列表、URL、分页数据或加载状态。
- 只显示当前用户本人通过应用列表可见的公司名；不得调用共享他人投递接口或未认证/公共公司目录。退出、用户变化和 `401` 清除缓存；网络失败可重试且不阻断手工搜索。

### 2. 默认拒绝末位排序

- API 缺省 `ordering` 或前端默认 `ordering=-updated_at` 时，在服务端先计算拒绝分组，再按 `rejected_bucket ASC, updated_at DESC, id DESC` 排序后分页。
- 有岗位公司仅当所有公开岗位的 APP-011 有效 `current_stage`（缺失时回退岗位 `application_status`）均为 `rejected` 才是拒绝公司；多岗位存在任一非拒绝岗位时归入非拒绝组。无岗位兼容 flat 公司使用顶层 `current_stage`，缺失时使用顶层 `application_status`。
- 明确选择其他合法 `ordering` 时不强插拒绝分组；既有排序白名单、搜索、筛选、分页单位和用户过滤不变。内部 `rejected_bucket` 不作为用户可传字段或响应字段。

### 3. 分页与查询状态

- HTTP 仍使用 `page`、`page_size`、`search`、`application_status`、日期筛选和 `ordering`；成功响应仍提供 `count/page/page_size/total_pages/next/previous/results`，链接保留全部查询条件。
- API `page` 为非正数、非整数、空值或小数时返回 `400 VALIDATION_ERROR`，详情指向 `page`；大于总页数时保留现有 `200` 空结果行为。`page_size` 仍只接受 `10/20/50/100`。
- UI 增加 `1..total_pages` 可选择页码和正整数输入跳转；输入越界或非法时不发请求、显示错误、保留所有查询条件。仅翻页修改 page；搜索、筛选、日期、排序、page_size 变更将 page 重置为 1。外部 URL 越界在获得响应后规范化到最后有效页，无数据规范化到 1。

## UI 输入、输出与错误行为

- 输入框 focus/click 打开建议面板，空输入显示本人去重公司名，非空输入按不区分大小写包含匹配；建议项显示公司名且提供 combobox/listbox 可观察语义。
- 点击建议项会填入公司名、关闭面板、以 `page=1` 执行一次普通搜索，同时保留当前 page_size、状态筛选、日期筛选和排序；手工输入/Enter/查询按钮继续使用现有接口。
- 建议为空或无匹配显示空状态，建议网络失败显示重试入口；建议 `401` 不得转为公共查询。
- 页码选择控件在 `total_pages=0` 时禁用；第一页/最后一页的上一页/下一页按边界禁用。非法页码包括空、空白、0、负数、小数、指数形式、非数字、超安全整数和超过总页数。

## 验收标准

- [x] 聚焦或点击关键字框可显示当前用户跨全部应用列表分页的去重公司名；建议只来自本人认证可见应用，未出现其他用户、共享他人或公共目录公司。
- [x] 建议项可被选择；选择后关键字、URL `search`、主列表请求一致，page 重置为 1，page_size、状态筛选、日期筛选和排序保持，且不发写请求或错误替换主列表。
- [x] 建议加载失败、401、空列表、无匹配和用户退出/切换均有隔离行为；手工输入、Enter、查询按钮未回归。
- [x] 缺省/default `-updated_at` 列表在服务端分页前把非拒绝公司排在完全拒绝公司前；多岗位公司混合状态归非拒绝组，稳定 tie-break 为 `updated_at DESC, id DESC`。
- [x] 显式合法非默认排序保持其原有语义；搜索、八值 `application_status`/`current_stage` 匹配、用户隔离和分页单位回归通过。
- [x] 主列表提供可选择页码和可输入页码跳转；任意合法页码请求保留 `page_size`、筛选、搜索、排序和日期状态，下一页/上一页仍正确。
- [x] 页码 1、最后页、无数据、越界 URL、非法输入和 API 非法参数均符合契约；UI 非法/越界输入不发请求并保留状态，API 非法 page 返回字段级 `400`。
- [x] 测试 Agent 提交稳定 `RED_CONFIRMED`；功能实现 Agent 提交 `READY_FOR_TEST`；测试 Agent 独立复测提交 `TEST_PASSED`；项目管理 Agent 收到通过报告后已完成验收并设置 `DONE`。

## 验收证据要求

测试和验收至少保留以下公开证据：

1. 两个合成用户的 HTTP 列表响应及建议触发请求，证明建议来源仅为当前认证用户且不调用共享/公共接口；跨多页、重复公司名、空列表、`401` 和请求失败各有结果。
2. 混合状态、拒绝单岗位、全拒绝多岗位、部分拒绝多岗位数据的 API 分页响应，记录默认排序、显式排序和跨页边界；不读取生产实现内部作为断言依据。
3. 前端公开交互或 DOM/HTTP 证据：focus/click 下拉、选择公司后搜索参数、查询状态保留、页码按钮、手工跳转、非法输入不发请求、首末页边界。
4. 现有搜索、八值状态筛选、日期筛选、排序、page_size、未认证 `401`、跨用户数据隔离和共享只读回归结果；报告必须区分本任务通过项与未运行项。

## 风险与测试边界

- 测试 Agent 只通过公开 HTTP API、公开 UI、URL 和请求/响应断言测试，不读取或分析 `backend/apps/`、`frontend/src/`；测试目录与报告目录是其唯一可写范围。
- 功能实现 Agent 只修改后端/前端生产代码及实现说明，把测试视为只读；排序必须在分页前完成，不能用当前页前端排序掩盖 API 分页错误。
- APP-011 的 `current_stage` 投影可能不同于保存的 `application_status`；测试拒绝末位必须使用公开有效投影契约，不能恢复旧的等值假设。
- 共享流程、面试时间、共享授权和当前用户 QuerySet 隔离是回归边界；任何跨用户泄露、建议读取共享接口或非法输入绕过都应按真实行为失败处理。

## Agent 交接

- 任务编号：`WEB-APP-008`
- 当前状态：`DONE`
- 发送角色：项目管理 Agent
- 接收角色：无（验收完成）
- 已完成内容与产物：产品契约 `docs/requirements/WEB-APP-008.md`、任务单 `docs/tasks/WEB-APP-008.md`；已冻结建议来源、拒绝分组算法、分页状态和错误行为。
- 测试 Agent 工作范围：仅在 `backend/tests/`、`frontend/tests/`、`tests/e2e/`、`docs/test-reports/` 编写黑盒测试；先证明建议、服务端排序和页码行为因缺失而稳定失败，再交实现 Agent。
- 功能实现 Agent 工作范围：在收到 `RED_CONFIRMED` 后仅修改 `backend/apps/`、`backend/config/`、`backend/manage.py`、`frontend/src/` 和 `docs/implementation-notes/`，不得修改测试、任务单或验收标准。
- 输入文档：本任务单、产品契约、APP-009/010/011 需求/任务/验收、WEB-APP-006/007 任务/验收、系统设计第 8、9、11、12 节、`docs/agents/project-manager.md`、`docs/agents/workflow.md`、`docs/agents/templates.md`。
- 建议测试顺序：公司建议来源/用户隔离 → 默认拒绝末位跨页排序 → page/page_size 与筛选/搜索/排序状态保留 → 页码选择/输入边界 → 前端回归。
- 本阶段完成条件：测试 Agent 已补齐本任务验收缺口并提交新的 `TEST_PASSED` 报告；项目管理 Agent 已完成逐条验收，所有交付物齐全，任务设置为 `DONE`。

## 2026-10-07 最终验收

- 项目管理 Agent 已核对最新 `docs/test-reports/WEB-APP-008-passed.md`：状态为 `TEST_PASSED`，专项后端 `15/15`、前端 `3/3`，指定命令退出码均为 `0`。
- 最新公开证据覆盖建议跨页读取/去重/选择、空列表/无匹配/`401`/`500`/重试隔离、默认拒绝末位排序及稳定 tie-break、多岗位混合状态、显式排序、既有查询与权限边界、页码首末边界/无数据/超页规范化、非法输入和分页参数保留。
- 验收结论：`ACCEPTED`。历史 WEB-APP-006 隔离 API 连接拒绝属于相邻未指定全量回归，不阻塞本任务专项验收。
- 回流角色：无。项目管理 Agent 已完成最终验收，本任务状态设置为 `DONE`。
