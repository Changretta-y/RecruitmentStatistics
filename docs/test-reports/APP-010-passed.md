# APP-010 TEST_PASSED

- 测试角色：测试 Agent
- 复测输入：`docs/implementation-notes/APP-010.md`，任务状态 `TEST_WRITING`，实现交接状态 `READY_FOR_TEST`
- 环境：Windows；Python 3.11.13；uv 0.7.21；按 `.nvmrc` 使用 Node 20.19.0；npm 10.8.2。后端测试均通过 `backend/tests/run-isolated-postgres.ps1` 使用隔离 PostgreSQL、合成用户和隔离数据完成。
- 变更范围：只修改 `backend/tests/`、`frontend/tests/` 和本报告；未修改生产实现、任务单或实现说明。

## 命令与结果

### APP-010 与 APP-009

- `& .\backend\tests\run-isolated-postgres.ps1 -MigrateOnly`：通过，迁移可应用。
- `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_010.py','--tb=no','-q')`：连续复测均为 **21 passed / 0 failed / 0 errors**。
- `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_009.py','--tb=no','-q')`：同步冲突断言后 **25 passed / 0 failed / 0 errors**。

APP-010 专项覆盖并通过：八值状态和默认值、非法/旧值拒绝及原子性、唯一状态来源、`current_stage` 等值只读投影、状态与日程解耦、历史迁移及字段保留、列表筛选、共享投影、跨用户隔离和多岗位状态隔离。

APP-009 保留并通过公司聚合、共享阶段唯一性、权限、流程/面试子资源、分页搜索、嵌套更新和原子性覆盖。

### 前端公开行为

- `npm run test -- tests/test_web_app_001.spec.ts tests/test_web_app_002.spec.ts tests/test_web_app_003.spec.ts tests/test_web_app_004.spec.ts tests/test_web_app_005.spec.ts`：**5 files passed / 46 tests passed**。
- `npm exec -- playwright test -- --config=tests/playwright.web_app_006.config.mts`：**12 passed**。
- `npm exec -- playwright test -- --config=tests/playwright.web_app_007.config.mts`：**5 passed**。
- `npm exec -- playwright test -- --config=tests/playwright.web_app_010.config.mts`：**3 passed**。
- `npm exec -- playwright test -- --config=tests/playwright.web_share_001.config.mts --grep "canonical status label"`：**1 passed**。

公开 UI 已验证八值选项及顺序、每个岗位只显示一个规范状态标签、筛选请求发送 `application_status` 且不发送 `stage`、多岗位状态展示和共享只读规范文案。

### 共享、日历、邮件独立回归

- `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_share_001.py','--tb=no','-q')`：**12 passed**。
- `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_cal_002.py','--tb=no','-q')`：最终 **15 passed / 0 failed / 0 errors**。
- `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_mail_001.py','--tb=no','-q')`：**9 passed**。
- `& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_mail_002.py','--tb=no','-q')`：最终 **11 passed / 0 failed / 0 errors**。

日历最终覆盖日期边界、跨午夜事件、六类事件字段和排序、超过 100 个事件、用户隔离、终态日程保留/清除删除、未认证和参数校验。邮件最终覆盖北京日汇总、跨午夜排序、空日安排、启用时间、重试/并发幂等、SMTP 拒绝、未知结果、配置诊断和敏感信息脱敏。

## 失败归因与契约同步记录

本轮日历和邮件第一次独立复测的失败均由旧测试输入触发，未形成实现回流：

1. `test_cal_002.py` 初始结果为 **6 passed / 9 errors**。所有错误使用 `_application_payload` 的 `application_status="in_progress"`；公开创建接口返回字段级 `400 VALIDATION_ERROR`，错误详情明确指出旧值不是合法选项。日历测试本身不验证业务状态，因此夹具同步为 `assessment` 后为 14/15 通过。
2. 日历终态用例随后唯一失败使用 `application_status="offer"`；公开接口同样返回字段级 400。按契约 `offer → rejected` 同步后，日历 **15/15** 通过。日历事件 `stage` 断言未修改。
3. `test_mail_002.py` 初始结果为 **8 passed / 3 failed**。三个失败都经过同一 `_create_application` 辅助函数提交 `in_progress`；不创建投递记录的其余八个用例通过。夹具同步为 `assessment` 后邮件 **11/11** 通过，说明失败不是汇总、重试、并发或脱敏行为。

APP-009 及受影响测试的映射如下，业务边界断言均保留：

| 旧测试契约 | APP-010 规范映射 | 保留的测试意图 |
|---|---|---|
| `in_progress` 测评场景 | `assessment` | 公司聚合/独立岗位和日程流程 |
| `in_progress` 二面场景 | `second_interview` | PATCH、嵌套流程和岗位隔离 |
| `offer` 终态/筛选场景 | `rejected` | 终态、搜索筛选和日程清除 |
| `withdrawn` 历史值 | `rejected` | APP-010 历史迁移公开结果 |
| 按日程派生 `current_stage` | 主岗位 `application_status` 等值投影 | 共享阶段唯一性、聚合和清除后的投影一致性 |

这些修改仅发生在测试夹具或与新契约直接冲突的断言中；没有删除 APP-009 聚合、权限、流程、分页或原子性覆盖，也没有放宽 APP-010 断言。

## 未覆盖风险

- 未运行全量前端测试套件、所有浏览器矩阵或全量后端回归；本报告只宣称列明命令的结果。
- 前端公开测试未覆盖视觉像素级回归、无障碍全量扫描和未列出的页面组合。
- 邮件真实外部 SMTP、真实第三方共享客户端及生产数据未验证；测试使用隔离数据库、合成用户和测试邮件后端。
- 既有工作区存在其他任务的生产/文档改动；本轮未读取、修改或依据这些生产实现作结论。

## 黑盒声明

严格依据任务单、需求契约、实现说明和公开测试契约工作；未读取、搜索、枚举或分析 `backend/apps/`、`frontend/src/`。测试只观察公开 HTTP 输入输出、认证/权限响应、迁移后的公开数据、邮件测试后端结果和浏览器公开行为。未修改生产代码、任务单或实现说明。

## Agent 交接

- 任务编号：APP-010
- 当前状态：`TEST_PASSED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent，进入验收
- 证据：`backend/tests/test_app_010.py`、`backend/tests/test_app_009.py`、日历/邮件/共享回归及前端公开测试；本报告记录全部命令、结果、归因和未覆盖风险。
