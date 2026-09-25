# MAIL-002 RED_CONFIRMED 每日安排邮件调度与发送

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；Python 3.11.13；uv 0.7.21；PostgreSQL 17.11；Asia/Shanghai
- 依赖同步：在 `backend/` 执行 `uv sync --frozen --group test`，成功
- 测试数据库：唯一基础库 `postgres_mail002_red_20260925_01`；pytest 使用 Django 隔离测试库。PostgreSQL 公共连接探针确认可连接，测试进程通过进程级 `DATABASE_URL` 指向该独立库。
- 临时配置：`SECRET_KEY` 使用每次运行新生成的测试值，未记录其内容；邮件后端使用 locmem 或测试专用替身，未连接真实 SMTP。
- 实现代码：未读取或修改。

## 专项运行

命令：

```text
uv run --no-sync pytest tests/test_mail_002.py --tb=no -q
```

命令在两次运行中均设置同一个独立 `DATABASE_URL` 和不同的进程级临时 `SECRET_KEY`。第一次结果为 `11 failed in 19.94s`；第二次结果为 `11 failed in 19.41s`。两次均为 0 passed、0 errors，所有测试项失败。

## RED 证据

11 条黑盒测试均通过公开注册/登录及 MAIL-001 通知设置和地址验证 API 建立用户；相关安排场景通过公开投递 API 建立数据。各测试在调用公开 Django 管理命令 `send_daily_summaries` 时稳定失败。直接执行：

```text
uv run --no-sync python manage.py send_daily_summaries
```

公开 CLI 输出：

```text
Unknown command: 'send_daily_summaries'
Type 'manage.py help' for usage.
```

因此缺失行为是每日发送公开管理命令尚未提供，不是测试语法、数据库、用户认证、邮件夹具或真实 SMTP 连接导致。pytest 使用 `--tb=no`，避免失败输出展示源码路径或片段。完整测试在两次运行中均只报告 11 项失败，没有测试错误。

## 编码覆盖的验收标准

测试文件 `backend/tests/test_mail_002.py` 以公开命令、locmem/可控邮件后端和通知设置 API 的 `last_delivery` 为观察点，编码以下断言。当前命令不存在，故本轮尚不能观察这些后续结果；实现后须由测试 Agent 按同一测试集复测：

- 到期的已验证启用用户收到按开始时间排序的当日摘要；包括跨入当天的事件；午夜前已结束及次日午夜才开始的事件排除；隔离其他用户日程；延迟运行可在同一北京时间日期补执行。
- 零安排时仍发送包含“今日无安排”的邮件；通知关闭、邮箱未验证或未到推送时刻的用户不发送。
- 用户在指定时间之后启用通知，当天不追发；后续日期只发送该日摘要，`last_delivery.date` 不回填旧日期。
- 同日重复执行与并发执行不产生重复 SMTP 接受；`last_delivery` 显示约定的 `{date, status}` 和状态值。
- SMTP 明确拒绝时记录 `failed_retryable`，同日至少等待 5 分钟再重试，最多 3 次重试；累计 4 次拒绝后进入终态 `failed`，之后不再尝试。单用户拒绝不妨碍其他用户发送。
- 重试前重新读取安排；投递删除后重试成功的摘要不再包含已删除公司，并正确报告空日。
- 发送结果不确定时记录 `unknown`，重复调用不自动重试。
- SMTP 配置缺失可观察且不伪报 `accepted`；命令输出、日志和设置响应不泄露 SMTP 密码、验证令牌、完整收件地址或邮件正文。

## 结果与交接

- 是否稳定复现：是。完整专项运行两次，均为 11 failed、0 passed、0 errors；公开 CLI 独立调用明确报告 `send_daily_summaries` 未注册。
- 回归结果：未运行相邻回归；已有认证和通知设置/验证 API 只作为测试夹具前置步骤，并在专项运行中成功。
- 未覆盖风险：管理命令缺失使发送记录状态转移、邮件内容、并发唯一 claim、SMTP 失败分类与重试策略尚未实际执行；相关公开断言已写入专项测试，待实现后复测。未验证真实 SMTP 服务商投递或收件箱送达。
- 黑盒声明：仅依据任务单、需求及已完成任务的公开 API 契约，通过注册、登录、投递、通知设置 API、公开管理命令和邮件后端替身验证；未读取或分析生产实现代码。

## Agent 交接

- 任务编号：`MAIL-002`
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent / 实现 Agent
- 已完成内容与产物：`backend/tests/test_mail_002.py`；本报告 `docs/test-reports/MAIL-002-red.md`
- 接收方工作范围：实现 `docs/tasks/MAIL-002.md` 定义的公开管理命令、每日汇总邮件、唯一发送记录、发送状态、有限重试及结果不确定处理。保持测试文件只读。
- 建议复测命令：`uv run --no-sync pytest tests/test_mail_002.py --tb=no -q`，并配置新的独立 PostgreSQL 测试库和临时 `SECRET_KEY`；邮件替身不得连接真实 SMTP。
- 结果或风险：RED 起因是公开 CLI 未提供 `send_daily_summaries`。完整业务断言在命令实现后继续验证。
- 本阶段完成条件：已满足；交项目管理 Agent 更新状态并移交实现阶段。
