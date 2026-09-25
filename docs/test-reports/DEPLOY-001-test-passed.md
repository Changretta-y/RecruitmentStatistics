# DEPLOY-001 TEST_PASSED 独立复测

- 测试角色：测试 Agent
- 结果：`TEST_PASSED`，当前实现七项配置合同检查全部通过（`7/7`）。本轮不重复运行 HEAD 基线；前一轮基线 `0/7` 的结果记录在 [DEPLOY-001-test-failed.md](DEPLOY-001-test-failed.md)。
- 环境：Windows PowerShell 7.6.5，本机无 Docker CLI；通过已配置 SSH 主机别名执行远端 Compose 5.1.0 配置解析。公开 Compose/Jenkins 文件副本和合成 env 放入独立 `/tmp/deploy-001-test-<GUID>`，本次目录为 `/tmp/deploy-001-test-0cd3236e9aec4a478151f9d6072939dc`，由脚本在结束时清理。没有启动、停止或修改运行服务。
- 命令：`& .\tests\e2e\deploy_001_compose_config.ps1`，退出码 `0`。
- 通过项：缺少 `DJANGO_SECRET_KEY`/`POSTGRES_PASSWORD` 时配置拒绝；无 SMTP 且邮件关闭时不启用 scheduler profile，Jenkins 停止/移除 scheduler 且部署命令不激活邮件 profile；SMTP 参数及 HTTP origin 传到 backend；启用邮件后 scheduler 具有 `daily-email` profile、调度命令和共享镜像，Jenkins 可控制 profile；scheduler 等待 backend `service_healthy`；release 分支 guard 支持 `BRANCH_NAME` 和 `GIT_BRANCH`；HTTP IP 配置关闭 SSL redirect、HSTS 与 Secure Cookie。
- 测试输入：继续使用测试脚本内的合成邮件主机、用户、密码、From 地址、HTTP IP、应用密钥和 URL-safe 数据库密码；不读取、复制或输出服务器 `.env` 值、真实 SMTP 凭据或 SSH 凭据。
- 未覆盖风险：仅验证远端 Compose 解析和静态 Jenkins 配置合同，没有执行 Jenkins 发布、实际迁移、数据库备份/权限验证、线上首页/API/日历冒烟或 SMTP 投递。生产运行结果仍需在经授权的发布流程中验证。
