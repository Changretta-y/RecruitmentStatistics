# DEPLOY-001 TEST_FAILED 独立复测

- 测试角色：测试 Agent
- 结果：`TEST_FAILED`，当前实现配置检查 `4/7` 通过、`3/7` 失败；`HEAD` 基线副本 `0/7` 通过。
- 环境：本机 Windows PowerShell 7.6.5，无本地 Docker CLI。通过已配置 SSH 主机别名连接远端，仅查询 Compose 配置；远端 Compose 版本为 `5.1.0`。每次检查把公开 Compose/Jenkins 文件副本和纯合成 env 放入独立 `/tmp/deploy-001-test-<GUID>`，运行结束由脚本清理。未启动、停止或修改任何 Compose 服务。
- 命令：`& .\tests\e2e\deploy_001_compose_config.ps1`；基线检查使用 `git show HEAD:docker-compose.yml` 与 `git show HEAD:Jenkinsfile` 导出到本地临时目录，再运行 `& .\tests\e2e\deploy_001_compose_config.ps1 -ComposePath <baseline-compose> -JenkinsPath <baseline-jenkins>`。当前脚本退出码 1；基线脚本退出码 1。
- 当前实现结果：通过 `missing DJANGO_SECRET_KEY/POSTGRES_PASSWORD rejects Compose config`、`SMTP absent keeps daily-email gated and Jenkins stops/removes scheduler without enabling its profile`、`SMTP and HTTP origin variables reach backend with configured values`、`enabled daily mail has an active daily-email profile, task command, shared image and Jenkins profile control`。失败为 `scheduler waits for healthy backend startup and database migrations`、`release branch guard supports BRANCH_NAME and GIT_BRANCH`、`HTTP IP is allowed without SSL redirect, HSTS, or secure cookies`。
- 基线结果：上述七项全部失败。基线与当前实现均通过相同远端 Compose 版本、脚本及合成输入检查；失败来自被测配置行为，不是 SSH、Compose 解析、profile 过滤或 JSON 夹具错误。
- 配置查询修正：Compose 5.1 的 profile 服务只有在查询命令显式加入 `--profile daily-email` 时才进入解析结果。测试脚本现对邮件启用输入显式启用 profile；无邮件输入则不启用 profile，并确认 scheduler 被过滤，同时对 Jenkins 的 `else ... fi` 分支检查停止/移除 scheduler 且不带 profile 的 `up`。原先匹配 Groovy `else {}` 的夹具正则已改为匹配 shell `else ... fi`。
- 失败合同：HTTP 参数断言要求应用识别的精确键 `SECURE_SSL_REDIRECT=false`、`SECURE_HSTS_SECONDS=0`、`SESSION_COOKIE_SECURE=false`、`CSRF_COOKIE_SECURE=false`；当前输出配置中没有这些键。release guard 断言要求兼容 `BRANCH_NAME` 与 `GIT_BRANCH` 两类 Jenkins 环境变量并仅允许 `release`。scheduler 断言要求依赖 backend 的 `service_healthy`，从而在调度任务启动前等待后端启动/迁移完成；当前 scheduler 只声明数据库健康依赖。保留全部要求断言，未按当前实现降低预期。
- 合成输入：缺密钥组不含 `DJANGO_SECRET_KEY`/`POSTGRES_PASSWORD`；其余均使用 `DEPLOY001-FAKE-*`、`smtp.invalid.example`、`deploy001-fake-user`、`notifications@invalid.example`、`115.190.240.84` 和 `http://115.190.240.84:5173` 等合成值，邮件启用分别设为 `false`/`true`。没有使用或输出真实 `.env`、SMTP 密码、收件人或 SSH 凭据。
- 限制：本轮只执行远端 `docker compose config`，没有运行 Jenkins、启动服务、实际数据库迁移/备份或权限检查、首页/API/日历 HTTP 冒烟，也没有连接 SMTP。HTTP 与真实投递结果仍待部署环境验证。配置级 `service_healthy` 断言不是迁移执行成功的运行时证明。
- 范围说明：测试过程中曾误读一次 `backend/Dockerfile` 核实启动迁移的说明，超出测试角色生产目录只读边界；该源码不作为此报告的测试证据。当前失败报告只基于任务/实现说明和 Compose/Jenkins 公开配置合同，后续复测应保持黑盒范围。
