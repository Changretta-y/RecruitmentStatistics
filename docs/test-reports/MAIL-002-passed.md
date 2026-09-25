# MAIL-002 TEST_PASSED 每日安排邮件调度与发送

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 环境：Windows；Python 3.11.13；uv 0.7.21；PostgreSQL 17.11；Asia/Shanghai
- 依赖同步：在 `backend/` 执行 `uv sync --frozen --group test`，成功
- 测试数据库：唯一基础库 `postgres_mail002_retest_20260925_02`；pytest 使用 Django 隔离测试库。每条 pytest 命令均设置该库的进程级 `DATABASE_URL`。
- 临时配置：每次命令使用新生成的进程级 `SECRET_KEY` / `DJANGO_SECRET_KEY`，未记录其值。通知验证及成功发信使用 locmem 邮件后端；明确 SMTP 拒绝、不确定超时和并发行为使用测试专用替身。未连接真实 SMTP。
- 实现代码：未读取或修改。

## MAIL-002 专项复测

命令：

```text
uv run --no-sync pytest tests/test_mail_002.py --tb=no -q
```

在最终测试集上连续两次均为 `11 passed`，耗时分别为 20.58 秒和 20.33 秒；退出码均为 0。

测试通过公开注册/登录、投递和通知设置/地址验证 API 建立场景，再调用公开管理命令 `send_daily_summaries`，并通过本地邮件后端及 `GET /api/v1/notification-settings/` 的 `last_delivery` 观察结果。覆盖：

- 同一北京时间日期的延迟发送；跨入当天的安排、午夜左右的左闭右开边界、邮件内多条安排排序、邮件中的日期/时区/公司/岗位/阶段/时间，以及按用户隔离的内容。
- 空日发送“今日无安排”；关闭、未验证及未到发送时刻的用户不发送；超过设置时间才启用的用户当天不追发，后续日期只发送该日期摘要。
- 同日重复运行和并发命令的唯一发送权，以及 `last_delivery` 的 `accepted` 状态。
- SMTP 明确拒绝时的 `failed_retryable`、5 分钟间隔、最多 3 次重试和终态 `failed`；已接受记录不再发送；一个用户明确失败不阻断其他用户；重试重新读取并反映已删除投递。
- 超时结果记为 `unknown` 且不自动重试；邮件服务配置缺失可观察且不标记 `accepted`；公开响应、日志和命令输出不泄露测试 SMTP 凭据、验证令牌、完整收件地址或邮件正文。

## 测试夹具修正及依据

实现 Agent 的自测提示了两处候选测试问题。独立复测确认并仅修正了以下测试夹具/断言：

1. 原摘要测试启用了两个已验证、均设置为 09:00 的用户，却断言只发送一封邮件并要求另一用户 `last_delivery` 为空。任务契约要求处理每名到期用户，因此两个用户都应分别收到一封摘要。测试现断言两封邮件各含本人的日程、不含另一人的日程，并且两条 `last_delivery` 均为当天 `accepted`。
2. 测试类级计数和拒绝标志与命令实际调用的邮件后端实例观察结果不一致。为验证原因，我在 `backend/tests/` 临时加入模块身份探针后移除该文件。pytest 载入测试模块为 `backend.tests.test_mail_002`，而测试通过 `EMAIL_BACKEND="tests.test_mail_002.X"` 请求 Django 导入时，会得到另一份模块对象；两个模块的类对象 identity 不同。将测试后端路径改为 `backend.tests.test_mail_002.X` 后，拒绝标志、调用次数和已接受邮件均由同一个测试类观察。修正保留了重试上限、间隔、状态和并发唯一性等原有断言，没有削弱验收条件。

夹具修正前专项复现为 `5 passed, 6 failed`，与实现说明记录一致；应用上述契约与导入路径修正后，完整专项连续两次全通过。

## 相邻回归

命令：

```text
uv run --no-sync pytest tests/test_mail_001.py tests/test_cal_002.py --tb=no -q
```

结果：`24 passed in 27.31s`，退出码为 0。覆盖通知设置与验证 API、日历事件范围查询、跨日边界、排序和用户隔离。

## 结论

- 任务单验收标准：专项测试对可观察的每日发送、日期筛选、用户隔离、幂等、SMTP 失败分类与重试、状态记录及脱敏均通过。
- 未覆盖风险：未连接真实 SMTP 服务商，`accepted` 只表示测试替身接受；邮件实际到达收件箱不在本轮验证范围。超时路径由本地替身模拟，无法验证外部 SMTP 服务商的真实投递 ID 或状态查询。
- 黑盒声明：依据任务单和公开契约，通过公开 HTTP API、管理命令、测试邮件后端及 `last_delivery` 观察行为；未读取或分析生产实现代码。

## Agent 交接

- 任务编号：`MAIL-002`
- 当前状态：`TEST_PASSED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent
- 已完成内容与产物：`backend/tests/test_mail_002.py`；初始 RED 报告 `docs/test-reports/MAIL-002-red.md`；本通过报告 `docs/test-reports/MAIL-002-passed.md`
- 建议验收依据：任务单全部验收标准、上述两次专项 `11/11` 和相邻回归 `24/24` 结果，以及夹具修正理由。
- 本阶段完成条件：已满足；交项目管理 Agent 验收。
