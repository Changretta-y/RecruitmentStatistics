# APP-011 RED_CONFIRMED

- 测试角色：测试 Agent
- 任务状态：`PLANNED`；本阶段完成后交项目管理 Agent，进入实现阶段
- 输入：`docs/tasks/APP-011.md`、`docs/requirements/APP-011.md`、`docs/acceptance/APP-010.md`、`docs/test-reports/APP-010-passed.md`
- 用户截图上下文：读取 APP-011 契约中对应的截图验收说明，并检查既有公开页面截图 `docs/test-reports/WEB-APP-007-desktop-default.png`；截图可见旧主列表“当前进度”仅显示“测评”并与共享流程区分，APP-011 新断言以公开 API 的 `current_stage` 和八值文案为准。
- 环境：Windows；Python 3.11.13；uv 0.7.21；按 `.nvmrc` 选择 Node.js 20.19.0；npm 10.8.2。后端通过项目既有 `backend/tests/run-isolated-postgres.ps1` 使用隔离 PostgreSQL、合成用户和隔离数据运行。
- 允许修改范围：仅 `backend/tests/`、`frontend/tests/`、本报告；未修改生产代码或任务单。

## 测试文件与命令

新增/调整的测试均为黑盒测试：

- `backend/tests/test_app_011.py`：APP-011 后端公开 API 专项。
- `frontend/tests/test_web_app_011.e2e.spec.ts`：APP-011 公开 UI/HTTP 夹具专项。
- `frontend/tests/playwright.web_app_011.config.mts`：该专项的测试运行配置。
- `frontend/tests/test_web_share_001.e2e.spec.ts`：将共享夹具的保存状态改为 `applied`、公开投影改为 `second_interview`，并把对应共享断言同步到 APP-011 新契约；本轮未单独运行该既有共享用例。

后端使用同一命令连续运行两次：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_011.py','--tb=no','-q')
```

两次结果均为：**14 passed / 10 failed / 0 errors**；分别耗时 41.00 秒和 28.45 秒。失败集合完全一致。

前端最小公开专项命令：

```powershell
nvm use 20.19.0
Set-Location frontend
npm exec -- playwright test -- --config=tests/playwright.web_app_011.config.mts --reporter=line
```

结果：**3 passed**。该专项未产生失败；其 HTTP 夹具直接提供了 APP-011 所需的 `current_stage`，前端下拉、主列表和筛选公开行为在当前测试夹具下通过。共享既有专项的新增投影断言本轮未启动，列入未覆盖风险。

## 覆盖的公开行为

### 后端

- 八个规范状态仍可写入并返回。
- `in_progress`、`offer`、`withdrawn`、`ai_interview`、旧中文和未知值返回字段级 `400 VALIDATION_ERROR`，且不创建公司。
- 公司共享 `assessment`、`written_test`、`ai_interview` 分别投影为 `assessment`、`written_test`、`other_interview`。
- 岗位“一面”“二面”“HR面”分别投影为 `first_interview`、`second_interview`、`hr_interview`；三面/复试/终面自定义名称投影为 `other_interview`。
- 最新时间优先；相同时间按 HR 面 > 其他轮次 > 二面 > 一面 > 笔试 > 测评；保存状态为 `rejected` 时终态优先；没有流程时间时回退保存状态。
- 流程投影变化不写回保存的 `application_status`，显式状态修改不改变流程时间/时长。
- 列表 `application_status` 筛选按有效 `current_stage` 匹配；共享只读响应与主列表投影一致。

### 前端

- 表单公开下拉只显示八项，顺序精确为：投递、测评、笔试、一面、二面、其他轮次、HR面、拒绝；不出现旧文案。
- 主列表公开岗位行读取 `current_stage` 展示最新状态，而不是固定显示保存值“投递”。
- 筛选请求使用 `application_status=second_interview`，不发送已废止的 `stage` 参数。

## RED 失败证据

稳定失败用例共 10 个：

- 7 个来源映射：共享测评、共享笔试、共享 AI 面、岗位一面、二面、HR 面、自定义终面。
- 1 个时间/固定优先级/拒绝终态/保存状态回退组合。
- 1 个流程投影与保存状态解耦及日程保留。
- 1 个列表按投影筛选和共享只读投影。

代表性失败的精简公开证据：创建 `application_status="applied"` 且共享测评有公开 `scheduled_at` 后，响应岗位公开字段仍为 `application_status="applied"`，`position.get("current_stage")` 实际为 `None`，期望为 `assessment`。失败发生在公开响应断言，不是导入、语法、数据库连接或测试夹具错误。

实际缺口表现为岗位级 `current_stage` 未返回/未按流程计算；其余失败分别证明当前实现尚未满足 APP-011 的来源映射、优先级、解耦、列表筛选和共享投影新行为。规范八值与旧值校验 14 项通过，说明隔离环境和既有 APP-010 状态契约可用。

## 回归与未覆盖风险

- APP-010 验收已读取；本阶段未重新运行 APP-010 全量专项，需实现后作为相邻回归复跑。
- APP-009 聚合/权限/流程/分页/原子性回归未在本阶段重新运行，需实现后复跑。
- 前端 APP-011 最小专项 3/3 通过；共享既有 `test_web_share_001.e2e.spec.ts` 的新增“保存状态与共享 `current_stage` 不同”用例未单独运行。
- 未运行全量前端套件、所有浏览器矩阵、视觉像素级回归或真实用户/真实 SMTP。
- 未覆盖所有自定义名称大小写/空格变体、同一映射值的稳定 ID 最终平局、分页多公司组合和拒绝后日程清除的完整矩阵；核心来源与固定优先级已有 RED 断言。

## 黑盒声明

严格依据 APP-011/APP-010 公开契约、验收记录和用户截图上下文工作；未读取、搜索、枚举或分析 `backend/apps/`、`frontend/src/`。只观察公开 HTTP 请求/响应、认证共享接口、公开迁移结果和可见浏览器 UI；未修改生产实现、任务单或质量门槛。

## Agent 交接

- 任务编号：APP-011
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent；请交功能实现 Agent 进入 `IMPLEMENTING`
- 产物：`backend/tests/test_app_011.py`、`frontend/tests/test_web_app_011.e2e.spec.ts`、`frontend/tests/playwright.web_app_011.config.mts`、本报告
- 回流依据：后端专项两次相同 **14 passed / 10 failed / 0 errors**，失败来自缺失 APP-011 最新流程状态公开投影及其列表/共享联动行为，不是环境、语法或夹具错误。
