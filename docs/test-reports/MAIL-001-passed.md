# MAIL-001 TEST_PASSED 通知设置与收件地址验证 API

- 测试角色：测试 Agent
- 环境：Windows；Python 3.11.13；uv 0.7.21；本机 PostgreSQL，定向测试库 `postgres_mail001_retest1_test`，认证/API 回归测试库 `postgres_mail001_regression2_test`。使用进程级临时 `SECRET_KEY`；未使用真实 SMTP。验证邮件成功路径使用 Django locmem 后端，SMTP 失败路径使用测试专用失败后端。
- 命令：`uv run --group test pytest tests/test_mail_001.py --tb=no -q`；`uv run --group test pytest tests/test_auth_001.py tests/test_auth_002.py tests/test_auth_003.py tests/test_auth_004.py tests/test_app_003.py --tb=no -q`。每条命令均设置独立 PostgreSQL `DATABASE_URL` 和临时测试密钥；报告中不记录其值。
- 通过 / 失败：MAIL-001 定向测试 9 / 0；认证与投递列表/详情隔离回归 38 / 0。两组测试均退出码 0。
- 公开输入：注册并登录用户后，通过公开 HTTP API 查询和修改通知设置、申请收件地址验证邮件、提交邮件链接中的令牌；SMTP 行为由测试邮件后端替身控制。
- 期望行为：仅本人可查看和修改设置；默认关闭且未验证；开启须先验证地址；新地址使旧验证失效并关闭推送；验证令牌一次性、限时且绑定用户和地址；每小时超过 3 次申请返回 `429`；SMTP 配置缺失或发送失败不伪报成功、不误标验证完成、不泄露令牌或凭据。
- 实际行为：定向测试 9 条全部通过，覆盖默认值、字段校验、认证保护、用户隔离、启用前置条件、邮箱更改、令牌确认/重放/用户及地址绑定/过期、申请限流、SMTP 缺失与发送失败。认证注册/登录以及投递列表/详情回归测试 38 条全部通过。
- 是否稳定复现：是；所有报告命令在独立测试数据库中完成，无数据库并发冲突或环境错误。
- 回归结果：`AUTH-001`、`AUTH-002`、`AUTH-003`、`AUTH-004` 与 `APP-003` 相关测试全通过。
- 覆盖的验收标准：MAIL-001 任务单全部四项验收标准。
- 未覆盖风险：真实部署 SMTP 的连接和收件人实际投递不属于测试范围；每日投递状态 `last_delivery` 由 MAIL-002 任务接入。
- 黑盒声明：未读取或分析生产实现代码，未修改测试断言；通过公开 HTTP 请求观察 API 行为。
