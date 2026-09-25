# CAL-002 RED_CONFIRMED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；Python 3.11.13；uv 0.7.21；PostgreSQL 17.11
- 依赖同步：在 `backend/` 执行 `uv sync --frozen --group test`，成功
- PostgreSQL 验证：Django 公共数据库连接探针返回 `vendor=postgresql`、版本 `170011`
- 测试数据库：独立数据库 `postgres_cal002_red_20260924_01`；pytest 使用 `postgres_cal002_red_20260924_01_test`
- 临时配置：测试进程的 `DATABASE_URL` 指向上述独立库；`SECRET_KEY` 为仅供测试的临时值，未记录凭据
- 实现代码：未读取或修改

## 专项结果

命令：

```text
uv run --no-sync pytest tests/test_cal_002.py --tb=short -q
```

结果：`15 failed`。相同最终测试集再次执行：

```text
uv run --no-sync pytest tests/test_cal_002.py --tb=no -q
```

结果：`15 failed in 16.20s`。连续运行均为 15 项失败、0 项通过、0 项测试错误。

## RED 证据

所有已认证场景在创建用户、登录和通过公开投递 API 建立测试记录后，调用 `GET /api/v1/calendar/events/` 均得到 HTTP `404`，预期的查询成功状态为 `200`。未认证场景同样得到 `404`，预期为 `401`。缺参、日期格式无效、结束日期不大于开始日期、跨度超过 42 天等输入也得到 `404`，预期为带 `VALIDATION_ERROR` 和参数字段标记的 `400`。

失败发生在日历 URL 的 HTTP 状态断言，Django 请求日志标记该路径 `Not Found`。注册、登录、投递创建及数据库初始化均成功；未出现语法错误、夹具错误、迁移错误或数据库连接错误。相同结果在独立 PostgreSQL 测试数据库中稳定复现，RED 来自日历查询公开行为尚未提供。

测试在日历返回契约后进一步断言日期窗口左闭右开、跨日相交、午夜结束边界、六阶段字段及结束时刻、按开始时间/投递 ID/阶段次序排序、101 条完整返回、空数组、用户隔离、终态保留、阶段清空和投递删除。当前公开路由返回 404，因此这些响应内容断言会在实现提供 200 后继续执行。

## 覆盖与交接

- 覆盖的验收标准：日期范围与左闭右开边界、跨日事件、事件字段及时长、六阶段、稳定排序、超过 100 条、无结果、认证与隔离、终态/清空/删除行为及日期参数错误。
- 未覆盖风险：API 尚未提供，故本轮 RED 执行只能直接观察到路由缺失；其余响应字段和筛选行为的断言已编码，需在实现后由测试 Agent 独立复测。
- 黑盒声明：仅根据任务单和需求，通过注册、登录、投递及日历公开 HTTP API 的输入输出验证；未读取或分析生产实现代码。

## Agent 交接

- 任务编号：`CAL-002`
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：实现 Agent
- 已完成内容与产物：`backend/tests/test_cal_002.py`；本 RED 报告 `docs/test-reports/CAL-002-red.md`
- 接收方工作范围：依据 `docs/tasks/CAL-002.md` 和 `docs/requirements/CAL-001.md` 第 3 节实现公开日期范围查询 API；测试文件及质量断言保持只读。
- 输入文档：CAL-002 任务单、CAL-001 第 3 节、APP-008 任务单与 `docs/test-reports/APP-008-passed.md`。
- 建议复测命令：`uv run --no-sync pytest tests/test_cal_002.py --tb=no -q`
- 结果或风险：时区固定为 `Asia/Shanghai`；测试使用专用 PostgreSQL 数据库，API 公开路由当前稳定返回 404。
- 本阶段完成条件：已满足；实现后由测试 Agent 按同一专项及必要回归独立复测。
