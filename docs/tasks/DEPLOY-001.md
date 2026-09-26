# DEPLOY-001 通过发布流水线部署日历与通知功能

- 状态：`DONE`
- 用户价值：通过现有 Jenkins `release` 流水线将已验收的日历、时长与通知功能安全部署到 HTTP 公网入口。
- 范围：Compose 生产变量、每日邮件调度容器、HTTP/IP 部署设置、Jenkins release 部署选择、发布前数据库备份和发布后冒烟。
- 非范围：购买/申请域名、配置 HTTPS、代管第三方邮箱、承诺 SMTP 收件箱送达、浏览器扩展发布。
- 依赖：`APP-008`、`WEB-APP-005`、`CAL-002`、`WEB-CAL-001`、`MAIL-001`、`MAIL-002`、`WEB-MAIL-001` 已完成；用户已授权实际部署。
- 允许修改范围：项目管理 Agent 仅 `docs/tasks/`、`docs/acceptance/`；测试 Agent 仅 `tests/e2e/` 与 `docs/test-reports/`；实现 Agent 仅 `docker-compose.yml`、`Jenkinsfile`、运行时/部署配置和 `docs/implementation-notes/`。

## 业务规则与公开契约

- 发布唯一入口为 Jenkins `RecruitmentStatistics-CI-CD` 的 `release` 分支轮询流水线；不得把未验收分支或测试专用环境发布到服务器。
- 公网以 `http://115.190.240.84:5173` 提供前端和同源 `/api/` 反代。`DJANGO_ALLOWED_HOSTS`、`CORS_ALLOWED_ORIGINS` 和 `FRONTEND_BASE_URL` 显式包含相应 HTTP IP 来源；HTTP 部署关闭 SSL 重定向、HSTS 和 Secure Cookie，不能遗留 HTTPS 强制跳转。
- Django 与 PostgreSQL 必需密钥不允许落到 Compose 开发默认值。数据库口令使用适合 URL 连接串的随机安全字符；数据库容器不发布公网端口，后端端口仅本机可达。
- Compose 将 `EMAIL_HOST`、`EMAIL_PORT`、`EMAIL_HOST_USER`、`EMAIL_HOST_PASSWORD`、`EMAIL_USE_TLS`、`EMAIL_USE_SSL`、`DEFAULT_FROM_EMAIL` 与 `FRONTEND_BASE_URL` 显式传给后端。SMTP 未配置时不启用每日调度容器；启用邮件需要明确的 `ENABLE_DAILY_EMAILS=true`，由同一已构建后端镜像每分钟调用 `send_daily_summaries`。停用标志时流水线确保调度容器停止。
- 发布前生成仅 root 可读的 PostgreSQL 备份；迁移由后端启动过程执行。发布后通过 Jenkins 冒烟检查前端首页、API health 和日历 API 的公开响应；失败时流水线标红并保留当前服务状态可诊断。

## 输入、输出与错误行为

- 输入：发布分支提交、服务器 `/opt/deploy/job/.env`、PostgreSQL 数据和 Jenkins 工具链。
- 缺少 `DJANGO_SECRET_KEY` 或 `POSTGRES_PASSWORD` 时 Compose 解析/发布必须失败，不回退开发口令。
- 邮件未配置时可部署应用与日历，但通知验证/发信 API 报告 SMTP 未配置；不得虚报邮件启用/送达。邮件参数完整且显式启用后才启动 scheduler。
- 发布失败不得删除数据库卷或数据库备份；前端/健康冒烟失败应使流水线失败。

## 验收标准

- [ ] Compose 使用必需的部署密钥、SMTP 环境变量传递和显式邮件调度启用条件；无秘密时不启动邮件调度。
- [ ] HTTP IP 访问不被重定向到 HTTPS，首页、日历及同源 API 正常；生产密钥和数据库口令不再使用开发默认值。
- [ ] Jenkins 从 `release` 分支构建并部署当前版本，迁移成功；公开 health、登录/日历 UI 冒烟成功。
- [ ] 部署前数据库备份存在且权限受限；SMTP 未配置时不发送或创建终态失败记录。
- [ ] 启用 SMTP 后，通知验证与发送链路可观察；启用 scheduler 后每日任务每分钟轮询并按功能任务契约处理。

## 风险与测试边界

- HTTP 无传输加密；本次按用户明确选择使用公网 IP/HTTP。后续增加域名和 HTTPS 前，不得开启 HSTS 或 HTTPS 强制跳转。
- 用户已说明将提供现有邮件账号/上游 SMTP 参数；发件地址须由 SMTP 服务商允许。未经配置前不能宣称通知邮件可发送。
- 发布测试使用 Compose 的测试变量、受控 health/API 请求及 Jenkins 运行结果；真实收件人投递只在用户配置实际 SMTP 后验证，不记录密码、完整测试邮件正文或令牌。

## Agent 交接

- 任务编号：`DEPLOY-001`
- 当前状态：`DONE`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent
- 已完成内容与产物：实现说明 `docs/implementation-notes/DEPLOY-001.md`；RED 配置测试 `tests/e2e/deploy_001_compose_config.ps1`、RED 报告 `docs/test-reports/DEPLOY-001-red.md`；独立复测失败报告 `docs/test-reports/DEPLOY-001-test-failed.md`；修复后独立通过报告 `docs/test-reports/DEPLOY-001-test-passed.md`（7/7）；生产验收记录 `docs/acceptance/DEPLOY-001.md`。
- 生产部署：Jenkins build #11 成功，revision `2db9b15` 已上线。发布备份 `/root/backups/job-20260926T121317Z.dump`（root、0600）；db/backend/frontend healthy；通知迁移成功；公网首页和日历路由 HTTP 200、health 冒烟成功、未认证日历 API 预期 401。
- 限制：SMTP 上游参数仍待用户提供，`ENABLE_DAILY_EMAILS=false`，邮件 scheduler 未启用；不得宣称真实投递已验证。
- 输入文档：本任务单、README 部署段、Jenkinsfile、`docs/acceptance/REL-001.md`、DEPLOY-001 RED 脚本/报告、实现说明及所有已完成业务任务通过报告。
- 建议命令：使用固定 SSH 别名将当前 Compose/Jenkins 副本复制到隔离临时目录，以合成 env 执行 `docker compose config`；enabled 测试显式使用 `--profile daily-email`。不得读取或修改 `/root/job/.env`、运行服务或打印真实凭据。
- 结果或风险：实现自检中必需密钥、SMTP 透传和 HTTP 安全检查通过；邮件 scheduler/profile 两项需独立复测，真实 SMTP 参数仍待用户提供。服务器真实数据库已生成 root-only 备份；本轮实现未触发部署。
- 已修复：scheduler 依赖 backend `service_healthy`；Jenkins release guard 兼容 `BRANCH_NAME`、`GIT_BRANCH` 等来源；HTTP 安全环境项改为 `SECURE_SSL_REDIRECT`、`SECURE_HSTS_SECONDS`、`SESSION_COOKIE_SECURE`、`CSRF_COOKIE_SECURE`。
- 本阶段完成条件：测试证据与生产流水线、备份、迁移和线上 HTTP 冒烟记录齐全后，由项目管理 Agent 标记 DONE。SMTP 后续启用和真实投递验证需另补配置记录。
