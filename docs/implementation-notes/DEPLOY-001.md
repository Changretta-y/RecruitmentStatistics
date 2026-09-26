# DEPLOY-001 实现说明

- 状态：`READY_FOR_TEST`
- 修改范围：`docker-compose.yml`、`Jenkinsfile`、本实现说明。
- 已实现行为：
  - Django secret key 和 PostgreSQL password 使用 Compose 必填插值；未提供时 `docker compose config` 失败，不回退开发口令。
  - PostgreSQL 不发布宿主机端口，Django 仅绑定宿主机 `127.0.0.1`；公网入口仍由前端 Nginx 的 HTTP `:5173` 服务提供。
  - Compose 显式向后端传 SMTP 七项配置及 `FRONTEND_BASE_URL`，默认 HTTP IP 来源；使用 Django 实际读取的 `SECURE_SSL_REDIRECT`、`SECURE_HSTS_SECONDS`、`SESSION_COOKIE_SECURE`、`CSRF_COOKIE_SECURE` 名称，HTTP 部署默认关闭这些安全属性。
  - 每日任务定义为 `daily-email` profile，使用与 backend 相同的 `job-backend:latest` 镜像，每分钟调用 `send_daily_summaries`；scheduler 等待 backend health check 成功，确保后端启动迁移完成后再运行。
  - Jenkins 在 `checkout scm` 后从 `BRANCH_NAME`、`GIT_BRANCH`、`GIT_LOCAL_BRANCH` 或 checkout 结果解析来源分支，并只允许 `release`；构建 backend/frontend 镜像。部署时只在 `ENABLE_DAILY_EMAILS=true` 且核心 SMTP 字段均非空时启用 `daily-email` profile。若显式启用但 SMTP 主机、端口、账号、密码或 From 地址缺失，部署在启动服务前失败。其他情况下先停止并移除现存 scheduler，再以无邮件 profile 部署。
  - 发布前 PostgreSQL 使用 `pg_dump -Fc` 备份。dump 暂存于 Jenkins agent 私有临时文件，再通过 Docker daemon 的 Alpine sidecar 写入宿主机 `/root/backups`；sidecar 将目录设为 `0700`、备份文件设为 `0600`。日志只记录备份文件名，不输出 dump 或密钥。
  - 部署后检查 HTTP 首页、`/calendar` SPA、health API，以及允许正常未认证 `401` 的日历 API 路由可达性。
- 数据库迁移：由 backend 容器现有启动流程运行；本任务没有新增迁移。
- 配置变化：服务器 `/opt/deploy/job/.env` 必须设置随机 `DJANGO_SECRET_KEY`、适用于 PostgreSQL URL 的 URL-safe `POSTGRES_PASSWORD`、正确 HTTP IP `DJANGO_ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS`/`FRONTEND_BASE_URL`。没有真实可用上游 SMTP 参数时保持 `ENABLE_DAILY_EMAILS` 未启用；邮件账户凭据未写入代码或提交文件。
- 已知限制：Jenkins agent 需要访问 Docker daemon，并且宿主机允许 daemon bind mount `/root/backups`。SMTP 实际连通、发件方授权和收件箱到达需要真实服务商配置后单独验证；本轮未触发发布，没有修改实际服务器 `.env` 或运行服务。HTTP 公网流量不加密。
- 运维权限要求：服务器 `/opt/deploy/job/.env` 必须由 root 管理，并以只读方式授权给 Jenkins 执行身份读取；例如文件属主为 `root`、属组为 Jenkins 专用组且权限为 `0640`。不得通过向 Jenkins 开放写权限或向其他用户开放读取权限解决访问问题。Jenkins release job #10 曾因文件不可读在环境检查阶段停止，Build、Backup、Deploy 均未执行，生产服务未改变；宿主机已由管理员调整为 root 管理并授予 Jenkins 组只读权限，容器内已验证可读。新的 release commit 会触发自动重跑。
- 自检结果：修复后通过 `tests/e2e/deploy_001_compose_config.ps1` 的七项合成配置检查。该脚本只将临时配置副本和合成环境变量传至隔离远端目录，执行 Compose `config`，没有启动/停止服务或读取服务器 `.env`；该实现自检不代替测试 Agent 独立复测。
- 建议复测命令：`& .\tests\e2e\deploy_001_compose_config.ps1`，并由测试角色分别用不含 SMTP 的合成环境确认 scheduler profile 未启用、用全套合成 SMTP 且 `ENABLE_DAILY_EMAILS=true` 确认 service/profile/命令和所有参数；不得启动或改动生产服务。
- 测试完整性声明：未修改测试脚本、断言或测试报告。
