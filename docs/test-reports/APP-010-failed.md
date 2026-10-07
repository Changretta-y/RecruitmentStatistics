# APP-010 TEST_FAILED

- 测试角色：测试 Agent
- 环境：Windows；Python 3.11.13（`.python-version`）；uv 0.7.21；Node.js 20.19.0（`.nvmrc`）；npm 10.8.2。后端通过仓库已有隔离 PostgreSQL 脚本运行，使用合成用户和隔离数据库；未访问生产数据。
- 实现输入：`docs/implementation-notes/APP-010.md`，状态 `READY_FOR_TEST`。
- 测试代码：`backend/tests/test_app_010.py`。为修正两处新增测试自身的公开契约定位错误，只调整了共享目标用户数据准备和迁移列表排序定位，未修改行为断言、既有测试或生产代码。

## 命令与结果

- `& .\backend\tests\run-isolated-postgres.ps1 -MigrateOnly`：通过，迁移已应用，无迁移错误。
- `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_010.py','--tb=no','-q')`：首次实现复测 `19 passed / 2 failed / 0 errors`；修正新增测试数据定位后连续两次均为 **21 passed / 0 failed / 0 errors**。
- `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_009.py','--tb=no','-q')`：**20 passed / 5 failed / 0 errors**。
- `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_share_001.py','tests/test_cal_002.py','tests/test_mail_001.py','tests/test_mail_002.py','--tb=no','-q')`：按用户要求中止长时间运行；中断前 **56 passed / 5 failed**，随后 `KeyboardInterrupt`。5 个已报告失败均来自 `test_cal_002.py`，共享/邮件套件未取得完整终态，不宣称通过。
- `git diff --check -- backend/tests/test_app_010.py`：通过。

## APP-010 专项公开证据

- 八个规范状态、默认 `applied`、旧值/未知值拒绝与原子性：通过。
- `current_stage` 等值只读投影、状态 PATCH 保留日程/时长、日程变更不反推业务状态：通过。
- `application_status` 单值/逗号分隔/重复参数筛选、任一岗位匹配以及旧 `stage` 参数拒绝：通过。
- 历史 `in_progress`、`offer`、`withdrawn` 迁移后的公开 canonical 状态、备注/链接/日程/时长保留：通过。
- 多岗位状态隔离、共享只读 canonical 投影和跨用户隔离：通过。共享测试数据已按公开契约使用“查看目标用户”的 URL 方向。

## 回归结果与失败路由

APP-009 有 5 个既有测试失败：

- `test_company_create_returns_multiple_independent_positions_and_shared_stages`
- `test_patch_adds_position_without_removing_omitted_positions_and_updates_shared_stage`
- `test_duplicate_shared_types_update_once_and_clear_date_clears_duration`
- `test_nested_interview_patch_keeps_omitted_siblings_and_defaults_durations`
- `test_search_status_filter_and_pagination_return_complete_company`

这些既有断言仍使用 APP-010 已废止的 `in_progress`/`offer` 状态或断言日程派生旧 `current_stage`，与当前 APP-010 契约冲突；测试 Agent 未修改它们来规避失败。公司聚合、共享流程、面试子资源、权限、分页/搜索的其余 APP-009 回归通过。由于相邻回归未全绿，本报告按 `TEST_FAILED` 交回项目管理 Agent 判定是否由项目管理 Agent 安排契约同步/兼容回归更新，再决定是否回实现 Agent。

共享/日历/邮件合并回归被用户中止，不能据部分结果判定；中断前日历失败需后续独立复跑。失败用例为：

- `test_date_window_is_left_closed_right_open_and_includes_crossing_events`
- `test_six_stage_events_have_public_fields_and_stable_order`
- `test_more_than_one_hundred_events_are_returned_without_application_pagination`
- `test_calendar_events_are_isolated_between_users`
- `test_terminal_application_keeps_scheduled_stage_and_clear_or_delete_removes_it`

这些失败尚未沿调用栈调查，避免越过生产实现黑盒边界。

## 未覆盖风险

- 前端公开 Playwright/Vitest 测试本轮未运行：八值表单选项顺序、单一状态标签、筛选只发送 `application_status` 且不发送 `stage`、多岗位状态卡和共享只读展示仍需后续独立复测。
- 共享、日历、邮件完整回归未取得终态；日历 5 项失败需先确认是否为 APP-010 对业务状态语义的预期影响或既存问题。
- `APP-009` 旧测试与 APP-010 新契约的状态枚举冲突需要项目管理 Agent 裁定，不由测试 Agent 修改任务单或放宽既有断言。

- 黑盒声明：未读取、搜索、枚举或分析 `backend/apps/`、`frontend/src/`；只通过公开 HTTP API、认证、共享响应、迁移后公开列表和既有测试目录中的公开 UI 契约工作。未修改生产代码、任务单或既有断言以规避失败。

## Agent 交接

- 任务编号：APP-010
- 当前状态：`TEST_FAILED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent；请根据 APP-009 旧断言冲突及未完成相邻回归，决定回实现 Agent 或先安排契约/回归测试协调。
- 产物：`backend/tests/test_app_010.py`、本报告 `docs/test-reports/APP-010-failed.md`。
- 建议后续：先复跑日历失败的独立用例；由项目管理 Agent 裁定 APP-009 旧状态测试的兼容回归口径；随后补跑前端公开测试。核心 APP-010 专项已稳定通过，无需修改生产实现来处理其已通过行为。
