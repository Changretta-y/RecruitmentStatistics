# MAIL-002 实现说明

- 状态：`READY_FOR_TEST`
- 修改范围：`backend/apps/notifications/`；未改测试、任务单、测试报告或全局运行配置。
- 已实现行为：新增公开 Django 管理命令 `send_daily_summaries`。命令按当前 `Asia/Shanghai` 日期和各用户设置的 `HH:mm` 处理已启用、地址已验证的通知；当天设置首次启用或更新时间晚于其发送时刻时跳过当天。相同北京日期内的延迟触发仍执行，过日后不补发旧日期。每次发送前按用户重新读取当前投递，查询当天 `[00:00, 次日 00:00)` 内相交的六阶段安排，含跨午夜安排，并按开始时刻、投递 ID 和阶段次序排序。空日邮件正文包含“今日无安排”。邮件显示北京日期、`Asia/Shanghai`、公司、岗位、阶段和本地开始/结束时间。
- 发送记录：新增 `DailyDelivery` 与唯一约束（通知设置 + 北京日期）；`GET /api/v1/notification-settings/` 的 `last_delivery` 返回最近日期及状态。通过数据库行锁取得发送权，重复和并发命令不会再次发送已在处理、已接受、终态失败或结果不确定的记录。
- 失败与重试：仅明确的 SMTP 收件人/数据拒绝进入可重试流程；首次投递后最多重试三次，每次至少间隔五分钟，并确保下一次尝试仍在当天 `23:59:59` 前。总尝试四次后或北京时间日界到达后转为 `failed`。发送连接异常、超时及非预期发送结果记为 `unknown`，不自动重试。明确缺少邮件主机或发件地址时记录终态 `failed` 并输出可观察诊断，不标记 `accepted`。进程在发送中断时会留下 `sending`；若进程恢复后该 claim 已超过 30 分钟，命令将其转为 `unknown`，过日的遗留 `sending` 也转为 `unknown`。
- 数据库迁移：新增 `notifications.0002_daily_delivery`，为通知设置记录变更时刻（先回填既有设置，再设为非空），并创建每日投递表、状态、尝试信息、可选投递 ID、日期/状态索引和用户日期唯一约束。
- 配置变化：无新增配置。继续使用 MAIL-001 的平台端 Django 邮件/SMTP 配置：`EMAIL_HOST`、`EMAIL_PORT`、`EMAIL_HOST_USER`、`EMAIL_HOST_PASSWORD`、`EMAIL_USE_TLS`、`EMAIL_USE_SSL`、`DEFAULT_FROM_EMAIL`。测试期间只使用 locmem 或本地测试后端，没有连接真实 SMTP。
- 日常调度：部署侧每分钟调用一次 `python manage.py send_daily_summaries`（可由系统计划任务、cron 或容器调度器执行）。重复触发安全；进程重启后，尚未领取的用户仍可执行，可重试失败按 `next_attempt_at` 等待。命令标准输出仅包含日期及聚合状态数；日志仅记录日期、用户 ID、结果状态和故障类别，不记录收件地址、邮件正文、验证令牌或 SMTP 凭据。监控命令的聚合 `failed`/`unknown` 数以及通知设置 API 的 `last_delivery`；排查具体 SMTP 接受情况时查看 SMTP 服务商投递日志或投递 ID。`unknown` 没有外部确认时须保持该状态，不能自动重发。
- 自检环境：Windows；Python 3.11.13；uv 0.7.21；本机 PostgreSQL 17.11；使用任务专用基础库 `postgres_mail002_impl_20260925_01`，pytest 隔离库为 `_test` 后缀；每次进程使用临时 `DJANGO_SECRET_KEY`。连接凭据和密钥未写入仓库或报告。
- 自检结果：`uv run python manage.py check` 通过；`uv run python manage.py makemigrations --check --dry-run` 报告无差异；`uv run ruff check apps/notifications` 通过。MAIL-001 回归专项 `uv run pytest tests/test_mail_001.py --tb=no -q --create-db` 为 9/9 通过。MAIL-002 指定专项 `uv run pytest tests/test_mail_002.py --tb=no -q` 为 `5 passed, 6 failed`。通过项包括空日、晚于发送时刻才启用、关闭/未验证/未到时跳过、缺少 SMTP 配置不伪报成功及诊断脱敏。另用任务专用基础 PostgreSQL 库、内存 SMTP 拒绝替身作本地自检：北京时间 09:00 明确拒绝后状态为 `failed_retryable`；09:04 不发送；09:05 执行下一次尝试并保持可重试状态。未连接真实 SMTP。
- 待测试 Agent 复核的断言问题：一条 MAIL-002 测试创建了两个均已验证、启用且到期的用户，但断言只允许一封邮件并要求第二用户无记录，与每个到期用户都要发送的任务契约冲突；多项自定义替身测试中命令结果状态已更新，但测试类上的计数/拒绝标志未反映发送后端执行（疑似测试模块重复导入造成状态隔离）。实现未通过违背公开契约的特判迎合该断言，也未修改测试。
- 已知限制：SMTP `accepted` 只代表邮件后端报告服务器接受；不代表收件人收件箱投递成功。SMTP 连接/提交后超时无法判断是否已接受，只能如实记录 `unknown` 并人工核对。
- 建议复测命令：在独立 PostgreSQL 测试库和临时 `DJANGO_SECRET_KEY` 环境中，于 `backend/` 执行 `uv run --no-sync pytest tests/test_mail_002.py --tb=no -q`。邮件使用测试替身，不连接真实 SMTP。
- 测试完整性声明：未修改测试、断言或质量门槛；实现自检不能替代测试 Agent 的独立复测。

## Agent 交接

- 任务编号：`MAIL-002`
- 当前状态：`READY_FOR_TEST`
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：每日摘要管理命令、`DailyDelivery` 迁移、`last_delivery` 输出；实现说明见本文件。
- 接收方工作范围：依据 MAIL-002 任务单及 RED 报告，从公开命令、测试邮件后端和通知设置 API 独立复测；核对前述两类测试结果并提交 `TEST_PASSED` 或 `TEST_FAILED` 报告。
- 输入文档：`docs/tasks/MAIL-002.md`、`docs/requirements/CAL-001.md` 第 5、8 节、`docs/test-reports/MAIL-002-red.md`、MAIL-001 与 CAL-002 公开通过报告。
- 建议命令：`uv run --no-sync pytest tests/test_mail_002.py --tb=no -q`；按 RED 报告为此次运行创建新独立 PostgreSQL 测试库并使用临时测试密钥。
- 结果或风险：Django 系统检查、迁移漂移检查和 Ruff 通过。专项自检发现上述测试夹具/替身问题，交独立测试角色核对；未使用真实 SMTP。
- 本阶段完成条件：测试 Agent 对任务契约和自检所发现问题完成独立复测并提交报告。
