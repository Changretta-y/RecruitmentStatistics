# APP-010 RED_CONFIRMED

- 测试角色：测试 Agent
- 环境：Windows；Python 3.11.13（根目录 `.python-version`）；uv 0.7.21；Node 20.19.0（`.nvmrc`）；npm 10.8.2。后端使用仓库已有隔离 PostgreSQL 脚本，合成数据库与合成用户，不访问生产数据。
- 命令：
  - `& .\backend\tests\run-isolated-postgres.ps1 -MigrateOnly`
  - `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_009.py','--tb=no','-q')`
  - `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_010.py','--tb=no','-q')`（连续两次）
  - `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_010.py::test_historical_status_values_migrate_to_canonical_public_statuses','--tb=no','-q')`（连续两次）
  - `git diff --check -- backend/tests/test_app_010.py`
- 通过 / 失败：APP-010 专项两次均为 **5 passed / 16 failed / 0 errors**；历史迁移用例两次均 **1 failed / 0 errors**，失败身份和数量稳定。APP-009 相邻公开回归 **25 passed / 0 failed**。未隔离 PostgreSQL 的首次 APP-009 运行产生 25 个环境 ERROR，未计入 RED；启动隔离库并执行迁移后基线恢复通过。

## 公开输入、期望与实际

- 八值状态：通过 nested `POST /api/v1/applications/` 分别提交 `applied`、`assessment`、`written_test`、`first_interview`、`second_interview`、`other_interview`、`hr_interview`、`rejected`；期望均为 `201`，岗位 `application_status`、兼容顶层 `application_status`/`current_stage`（若存在）与输入相等。另以省略字段创建，期望缺省为 `applied`。实际：既有公开行为对六个新增阶段值未达到成功/等值投影断言；默认 `applied` 基线通过。
- 非法值与原子性：提交 `in_progress`、`offer`、`withdrawn`、`ai_interview`、中文展示名和未知值，并夹带一个合法岗位；期望 `400 VALIDATION_ERROR`、错误详情指向 `application_status` 且公司数量不增加。实际：旧值场景未稳定满足字段级拒绝和无副作用断言；未知值的既有校验不代表新八值契约已实现。
- 唯一状态来源与日程解耦：创建带测评日期/时长和面试日期/时长的 `applied` 岗位，再 PATCH 为 `second_interview`；期望只改变岗位业务状态，顶层兼容状态等值投影，所有日期/时长保留。新增、清空测评日期和新增面试也应保持 `application_status=applied`、`current_stage=applied`。实际：日期/面试公开输入会影响兼容阶段断言，说明当前行为仍按日程派生状态；专项状态解耦断言失败。
- 列表筛选：以同一公司两个岗位分别写入 `applied`、`second_interview`，使用单值、逗号分隔和重复 `application_status` 参数；期望按任一岗位匹配且分页单位为公司。传入旧 `application_status=in_progress` 或 `stage=first_interview` 期望 `400 VALIDATION_ERROR` 并分别指向对应字段。实际：canonical 状态筛选/旧 `stage` 拒绝断言失败。
- flat 兼容写入：提交公开兼容 flat body 的 `application_status=hr_interview`；期望主岗位、顶层 `application_status` 和 `current_stage` 同为 `hr_interview`。实际：canonical flat 写入/等值投影断言失败。
- 多岗位与共享投影：同一公司两个岗位分别保存状态，PATCH 第二岗位后第一岗位不变；未授权用户仍为 `404`；建立公开共享授权后，共享只读响应应只呈现主岗位 canonical 状态且与 `current_stage` 相等。实际：多岗位 canonical 状态和共享投影专项失败；既有跨用户隔离基线未被本专项改动。
- 历史迁移：在公开既有迁移基线 `applications.0003_jobapplication_stage_durations` 播种 `in_progress`（笔试/一面/二面/三面/HR、仅 AI、无可映射流程）、`offer`、`withdrawn`、`applied`、`rejected`，迁移到当前叶节点后只读取列表 API。期望分别得到 `written_test`、`first_interview`、`second_interview`、`other_interview`、`hr_interview`、`applied`、`applied`、`rejected`、`rejected`、原值，并保留备注、链接、日程及 42 分钟时长。实际：迁移后的公开状态断言失败；无 ERROR，且连续两次稳定复现。

## 覆盖的验收标准

- [x] 八个规范状态、默认 `applied`、旧值/未知值字段级拒绝和失败原子性。
- [x] 岗位状态 PATCH、兼容顶层等值投影、状态与日程/时长解耦。
- [x] `application_status` 单值/逗号分隔/重复参数筛选、`stage` 参数拒绝。
- [x] 历史旧值公开迁移结果、字段/日程/时长保留。
- [x] 多岗位状态独立、主岗位共享投影、跨用户隔离。
- [x] APP-009 公司聚合/嵌套流程相邻回归 25/25 通过。

## 未覆盖风险

- 本轮按用户要求优先完成后端最小可靠 RED，尚未新增前端 `ApplicationForm.vue`、`ApplicationsView.vue`、岗位卡和共享页面的公开 UI 测试；实现完成后需由测试 Agent 补充或复测八值选项、单状态标签、筛选 URL/API 字段及共享只读展示。
- 日历、提醒、邮件和完整共享回归未在本轮专项重复执行；APP-009 基线仅证明公司聚合公开契约未受测试改动影响。
- 迁移表中“历史测评日程”在既有 `0003` 固定字段基线中没有独立测评字段，本轮通过 canonical `assessment` API 接收和日程解耦覆盖其公开行为；实现 Agent 应在迁移说明中补充实际数据来源与数量。

- 是否稳定复现：是。APP-010 完整专项连续两次相同为 5/16；迁移用例连续两次失败，均为公开行为断言，不是语法、夹具、迁移启动或数据库连接错误。
- 回归结果：APP-009 定向测试在隔离 PostgreSQL 中 25/25 通过；未宣称全项目全绿。首次未注入 `DATABASE_URL` 的运行仅记录为环境排障，不作为任务 RED 证据。
- 黑盒声明：未读取、搜索、枚举或分析 `backend/apps/`、`frontend/src/` 生产实现；测试只通过 HTTP API、公开认证、公开共享响应和迁移后的公开列表响应观察输入输出。未修改任务单或生产代码。

## Agent 交接

- 任务编号：APP-010
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent；请由项目管理 Agent 按流程转交功能实现 Agent，进入 `IMPLEMENTING`。
- 产物：`backend/tests/test_app_010.py`、本报告 `docs/test-reports/APP-010-red.md`。
- 实现范围：仅修复生产实现和迁移；测试目录视为只读，不放宽断言或修改质量门槛。
- 建议复测命令：`& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_010.py','--tb=no','-q')`，随后运行 APP-009 及项目管理 Agent 指定的共享/日历/邮件相邻回归。
- 本阶段完成条件：功能实现完成并提交 `READY_FOR_TEST` 说明后，由本测试角色独立复测相同专项和必要回归，产出 `TEST_PASSED` 或 `TEST_FAILED`。
