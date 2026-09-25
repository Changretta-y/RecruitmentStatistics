# CAL-002 TEST_PASSED

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 环境：Windows；Python 3.11.13；uv 0.7.21；PostgreSQL 17.11
- 依赖同步：在 `backend/` 执行 `uv sync --frozen --group test`，成功
- 测试数据库：独立数据库 `postgres_cal002_retest_20260925_01`；pytest 使用 `postgres_cal002_retest_20260925_01_test`
- 临时配置：测试进程 `DATABASE_URL` 指向上述独立库；`SECRET_KEY` 为仅供测试的临时值，未记录凭据
- 实现代码：未读取或修改

## CAL-002 专项复测

命令：

```text
uv run --no-sync pytest tests/test_cal_002.py --tb=no -q
```

结果：`15 passed in 16.83s`。

测试通过注册、登录及投递公开 API 建立记录，覆盖北京时间日期窗口左闭右开、跨日相交及原始起止时间、恰好午夜结束/开始边界、六阶段事件字段与时长、开始时刻/投递 ID/阶段次序稳定排序、101 条事件完整返回、无结果、未认证、跨用户隔离、终态投递保留，以及阶段清空和投递删除后的事件移除。缺参、日期格式错误、无效日期、相等/反向区间和超过 42 天分别验证 `400 VALIDATION_ERROR` 及参数标记。

另在同一独立数据库完成迁移后，以注册、登录和日历 HTTP API 探针验证范围上限：42 天空范围返回 `200` 和空事件数组；43 天范围返回 `400`。探针使用 `2026-09-01` 至 `2026-10-13`（42 天），以及至 `2026-10-14`（43 天）。

## 相邻回归

命令：

```text
uv run --no-sync pytest tests/test_app_002.py tests/test_app_003.py tests/test_app_006.py tests/test_app_007.py tests/test_app_008.py tests/test_auth_001.py tests/test_auth_002.py tests/test_auth_003.py tests/test_auth_004.py tests/test_urls.py --tb=no -q
```

结果：`138 passed in 139.18s`。覆盖投递创建、详情、更新、阶段时长、删除、认证、JWT 权限边界及 URL 回归。

## 结论

CAL-002 专项和相邻回归均通过。42 天有效上限与 43 天拒绝边界也通过公开 HTTP 输入输出确认。未观察到日期筛选、排序、分页、用户隔离、认证或输入校验行为失败。

- 覆盖的验收标准：CAL-002 全部验收标准。
- 未覆盖风险：未测量极大量事件下的性能和查询次数；契约规定的 101 条完整返回及 42 天查询范围均已覆盖。
- 黑盒声明：仅依据任务单、需求、实现说明和公开 HTTP API 行为复测；未读取或分析生产实现代码，未修改测试或断言。

## Agent 交接

- 任务编号：`CAL-002`
- 当前状态：`TEST_PASSED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent
- 已完成内容与产物：`backend/tests/test_cal_002.py`；RED 报告 `docs/test-reports/CAL-002-red.md`；本独立通过报告 `docs/test-reports/CAL-002-passed.md`
- 接收方工作范围：根据 CAL-002 任务单、公开需求和 RED/通过证据进行验收并记录结论。
- 输入文档：`docs/tasks/CAL-002.md`、`docs/requirements/CAL-001.md` 第 3 节、`docs/implementation-notes/CAL-002.md`、APP-008 公开任务契约及通过报告。
- 建议命令：`uv run --no-sync pytest tests/test_cal_002.py --tb=no -q`
- 结果或风险：专项 15/15 通过；相邻投递、认证与 URL 回归 138/138 通过；范围上限 HTTP 探针通过。
- 本阶段完成条件：已满足；交项目管理 Agent 验收。
