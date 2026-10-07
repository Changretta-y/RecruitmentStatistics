# APP-011 TEST_PASSED

- 测试角色：测试 Agent
- 复测输入：`docs/tasks/APP-011.md`、`docs/requirements/APP-011.md`、`docs/test-reports/APP-011-red.md`、`docs/test-reports/APP-011-failed.md`、`docs/implementation-notes/APP-011.md`、`docs/acceptance/APP-010.md`
- 实现状态：`READY_FOR_TEST`
- 环境：Windows；Python 3.11.13；uv 0.7.21；按 `.nvmrc` 使用 Node.js 20.19.0；npm 10.8.2；后端通过项目隔离 PostgreSQL 脚本运行，使用合成用户和隔离数据。
- 修改范围：只修改 `backend/tests/`、`frontend/tests/` 和本报告；未修改生产代码、任务单或实现说明。

## 测试命令与结果

### APP-011 专项

```powershell
& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_011.py','--tb=no','-q')
```

同一命令连续独立运行两次：

- 第一次：**24 passed / 0 failed / 0 errors**，27.08 秒
- 第二次：**24 passed / 0 failed / 0 errors**，26.93 秒

覆盖八值及旧值拒绝、共享测评/笔试/AI 面、岗位一面/二面/HR 面/自定义面试映射，最新时间、同刻固定优先级、拒绝优先、无流程回退、状态与日程解耦、列表按投影筛选和共享只读投影。

### 相邻 API 回归

- APP-010：`tests/test_app_010.py`，**21 passed / 0 failed / 0 errors**，24.81 秒。
- APP-009：`tests/test_app_009.py`，**25 passed / 0 failed / 0 errors**，30.50 秒。
- 共享：`tests/test_share_001.py`，**42 passed / 0 failed**，95.25 秒。并发用例结束时有 PostgreSQL 测试库 teardown warning（仍有两个连接），无测试失败。
- 日历：`tests/test_cal_002.py`，**15 passed / 0 failed / 0 errors**，18.11 秒。
- MAIL-001：`tests/test_mail_001.py`，**9 passed / 0 failed / 0 errors**，11.61 秒。
- MAIL-002：`tests/test_mail_002.py`，**11 passed / 0 failed / 0 errors**，21.56 秒。

### 前端公开专项

```powershell
nvm use 20.19.0
Set-Location frontend
npm exec -- playwright test -- --config=tests/playwright.web_app_011.config.mts --reporter=line
```

结果：**3 passed**。覆盖八项下拉精确顺序和旧文案排除、主列表使用公开 `current_stage`、筛选请求使用 `application_status` 且不发送 `stage`。

## PM 授权的测试契约同步

仅更新测试目录中与 APP-011 新契约冲突的断言，保留原业务覆盖：

| 旧断言/夹具 | 新断言/契约 | 保留内容 |
|---|---|---|
| APP-011 逐字比较 `2026-10-22T09:00:00+08:00` | 解析 ISO 8601 带时区值后比较 UTC 瞬时值；等值 `2026-10-22T01:00:00Z` 通过 | 时间存在性、时长保留、状态解耦和清空/更新行为 |
| APP-010 创建后有测评与“技术面”时断言 `current_stage=applied` | 按最新候选和自定义面试映射断言 `current_stage=other_interview` | 保存状态仍为 `applied`、状态 PATCH 保留共享流程/岗位面试和时长 |
| APP-010 状态 PATCH 后断言 `current_stage=second_interview` | 仍有同刻最新自定义流程时断言 `current_stage=other_interview` | 显式保存状态为 `second_interview`，流程数据不被改写 |
| APP-010 新增测评/一面日程后断言 `current_stage=applied` | 分别断言 `assessment`、`first_interview`；清空后回退 `applied` | `application_status` 不被日程隐式改写，清空联动保留 |
| APP-009 共享测评后断言顶层投影等于保存状态 | 断言最新共享测评为 `assessment`；清空后回退 `applied` | 共享类型去重、更新时间、清空时长、聚合结构 |
| APP-009 嵌套面试后断言顶层投影等于保存状态 | 最新自定义复试为 `other_interview`；更新后一面时间更晚则为 `first_interview` | 兄弟面试保留、默认时长、嵌套 PATCH 和流程子资源 |

未删除或放宽 APP-009 的聚合、权限、分页、搜索、隔离、流程、时长和原子性断言；未恢复 APP-010 的旧等值语义。

## 时间格式失败的裁定结果

此前 APP-011 唯一失败是测试逐字比较输入偏移量与 API UTC `Z` 输出。按 PM 更新契约，测试改为解析带时区时间并比较瞬时值；没有改变公开 API 的时间格式要求，也没有放宽时间字段、时长或解耦断言。修改后 APP-011 连续两次全绿。

## 未覆盖风险

- 未运行全量后端/前端套件、所有浏览器矩阵、视觉像素级和全量无障碍检查。
- 共享并发用例的测试数据库 teardown 仍有连接关闭 warning；42 项业务断言全部通过，建议后续单独清理测试运行器连接生命周期。
- 邮件使用隔离测试邮件后端，不证明真实 SMTP 服务商和真实收件箱送达。
- 未验证真实第三方共享客户端；共享公开 API、权限隔离和只读字段已由专项覆盖。

## 黑盒声明

严格依据 APP-011/APP-010 公开契约、PM 裁定和实现说明复测；未读取、搜索、枚举或分析 `backend/apps/`、`frontend/src/`。仅观察公开 HTTP 输入输出、认证/共享响应、隔离迁移结果和公开浏览器行为。未修改生产代码、任务单或实现说明。

## Agent 交接

- 任务编号：APP-011
- 当前状态：`TEST_PASSED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent，进入验收
- 证据：APP-011 后端两次 24/24、APP-010 21/21、APP-009 25/25、前端 3/3、共享 42/42、日历 15/15、MAIL-001 9/9、MAIL-002 11/11。
