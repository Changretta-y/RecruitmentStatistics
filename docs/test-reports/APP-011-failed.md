# APP-011 TEST_FAILED

- 测试角色：测试 Agent
- 复测输入：`docs/tasks/APP-011.md`、`docs/requirements/APP-011.md`、`docs/test-reports/APP-011-red.md`、`docs/implementation-notes/APP-011.md`、测试 Agent 规范及 APP-010 验收记录。
- 实现交接状态：`READY_FOR_TEST`
- 环境：Windows；Python 3.11.13；uv 0.7.21；按 `.nvmrc` 使用 Node.js 20.19.0；npm 10.8.2；后端使用隔离 PostgreSQL、合成用户和隔离数据。
- 变更范围：本轮未修改生产代码、任务单或既有断言；只生成本报告。

## APP-011 专项

原样连续运行两次：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_011.py','--tb=no','-q')
```

两次结果完全一致：

- 第一次：**23 passed / 1 failed / 0 errors**，27.62 秒
- 第二次：**23 passed / 1 failed / 0 errors**，28.56 秒
- 唯一失败：`test_schedule_projection_and_saved_status_are_independent`

精简公开失败证据：

```text
期望：2026-10-22T09:00:00+08:00
实际：2026-10-22T01:00:00Z
```

公开响应中的时间点与输入是同一瞬间；失败发生在测试对 `shared_stages[*].scheduled_at` 的字符串逐字相等断言，不涉及 `current_stage` 映射、保存状态、日程存在性或时长丢失。APP-011 实现说明已经报告同一自检失败。

本轮未修改该断言，也未把时间格式差异擅自放宽为自定义比较。该项属于测试断言与既有 APP-009/APP-010 公开时间序列化格式之间的契约裁定问题，请 PM 明确是否允许测试 Agent 以既有 UTC `Z` 公开格式调整断言；在裁定前不将其回流为实现行为缺陷。

APP-011 其余新增行为通过：八值及旧值校验、各共享/岗位来源映射、最新时间与固定优先级、拒绝优先、无流程回退、列表/共享投影及前端专项均未出现其他失败。

## 前端专项

```powershell
nvm use 20.19.0
Set-Location frontend
npm exec -- playwright test -- --config=tests/playwright.web_app_011.config.mts --reporter=line
```

结果：**3 passed**。覆盖八值下拉顺序和旧文案排除、主列表使用 `current_stage`、筛选使用 `application_status` 且不发送 `stage`。

## 相邻回归

- APP-010：**19 passed / 2 failed**。失败为既有 `current_stage == application_status` 断言，与 APP-011 已修订的最新流程投影契约冲突：
  - `test_status_patch_updates_projection_but_preserves_schedule_and_duration`
  - `test_schedule_changes_do_not_derive_or_change_application_status`
  八值、历史迁移、状态写入、日程字段保留等其余断言通过；未修改既有断言。
- APP-009：**23 passed / 2 failed**。失败为既有顶层 `current_stage == positions[0].application_status` 断言，与 APP-011 允许流程投影不同于保存状态的契约冲突：
  - `test_duplicate_shared_types_update_once_and_clear_date_clears_duration`
  - `test_nested_interview_patch_keeps_omitted_siblings_and_defaults_durations`
  聚合、权限、流程子资源、分页、搜索和原子性其余断言通过；未修改既有断言。
- 共享：**42 passed / 0 failed**；并发用例结束时出现 PostgreSQL 测试库 teardown warning（仍有 2 个连接），没有测试失败。
- 日历：**15 passed / 0 failed**。
- MAIL-001：**9 passed / 0 failed**；命令在报告请求前已自然完成，未继续运行 MAIL-002。
- MAIL-002：本轮未运行，因用户要求先结束长回归并先报告当前 APP-011 结果。

## 失败归因与路由

1. APP-011 唯一失败是公开时间字符串表示差异，`+08:00` 与 `Z` 表示相同时间点；没有证据表明实现丢失或错误改写日程。该项等待 PM 契约裁定，测试 Agent 未自行修正。
2. APP-010/APP-009 两组失败是相邻既有断言仍要求旧的等值 `current_stage` 语义；这与 APP-011 任务明确引入的最新流程投影冲突，不能据此要求实现恢复旧行为。需 PM 裁定是否同步相邻测试断言后再做最终验收。
3. MAIL-002 尚未取得终态，不宣称相关回归全部通过。

## 未覆盖风险

- MAIL-002 本轮未运行；真实 SMTP、真实共享客户端和全量回归未验证。
- APP-011 共享前端新增断言未单独运行；共享后端专项已通过。
- 未运行全量前端套件、浏览器矩阵、视觉像素级或无障碍全量检查。

## 黑盒声明

未读取、搜索、枚举或分析 `backend/apps/`、`frontend/src/`；仅依据任务/需求、实现说明、公开 HTTP 请求响应、公开 UI、共享接口和既有测试契约复测。未修改生产代码、任务单或既有断言。

## Agent 交接

- 任务编号：APP-011
- 当前状态：`TEST_FAILED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent；请先裁定时间序列化断言和 APP-010/APP-009 相邻旧断言口径，再决定是否回实现 Agent或测试 Agent。
- 产物：本报告；已有 `docs/test-reports/APP-011-red.md`、后端专项和前端专项测试。
