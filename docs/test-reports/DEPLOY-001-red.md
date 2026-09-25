# DEPLOY-001 RED_CONFIRMED 发布配置与邮件调度

- 测试角色：测试 Agent
- 环境：本机 Windows PowerShell；本机无 Docker CLI。通过已配置 SSH 主机别名 `huoshan` 连接远端，只查询 `docker compose version`，版本 `5.1.0`。远端配置检查使用每次单独创建的 `/tmp/deploy-001-test-<GUID>` 目录；最近一次为 `/tmp/deploy-001-test-813640814b6941f58ee65ee6d6faf616`，脚本退出时已删除。Docker Compose 只执行 `config`，未启动、停止或修改任何运行服务。
- 命令：`& .\tests\e2e\deploy_001_compose_config.ps1`，连续运行两次；脚本在远端临时目录复制本地 `docker-compose.yml` 与 `Jenkinsfile`，使用临时合成环境文件运行远端 `docker compose config --quiet`/`config --format json`。最终修订增加了对 SSH 进程中同名环境变量的显式 unset，确保仅由合成环境文件驱动解析。
- 通过 / 失败：两次均为 `0 passed / 5 failed`，退出码 1；Compose 配置解析命令正常完成，没有 SSH、路径、JSON 或测试夹具错误。
- 公开输入：缺密钥场景不提供 `DJANGO_SECRET_KEY` 和 `POSTGRES_PASSWORD`；无邮件场景提供合成应用密钥和 `ENABLE_DAILY_EMAILS=false`，不提供 SMTP 值；邮件启用场景提供合成 SMTP 参数并设置 `ENABLE_DAILY_EMAILS=true`。脚本只向输出写检查名称及通过/失败状态。
- 合成值：`DJANGO_SECRET_KEY=DEPLOY001-FAKE-DJANGO-ONLY`、`POSTGRES_PASSWORD=DEPLOY001-FAKE-DB-URL_SAFE-5421`、`EMAIL_HOST=smtp.invalid.example`、`EMAIL_PORT=2525`、`EMAIL_HOST_USER=deploy001-fake-user`、`EMAIL_HOST_PASSWORD=DEPLOY001-FAKE-SMTP-ONLY`、`EMAIL_USE_TLS=true`、`EMAIL_USE_SSL=false`、`DEFAULT_FROM_EMAIL=notifications@invalid.example`、`DJANGO_ALLOWED_HOSTS=115.190.240.84,localhost,127.0.0.1`、`CORS_ALLOWED_ORIGINS=http://115.190.240.84:5173`、`FRONTEND_BASE_URL=http://115.190.240.84:5173`、`FRONTEND_PORT=5173`、`ENABLE_DAILY_EMAILS=false/true`。以上全部为临时测试值，不用于真实服务。
- 期望行为：缺少 Django/数据库必需密钥时 Compose 配置失败；未配置 SMTP 时 scheduler 有声明但保持非活动 profile；SMTP 完整且邮件显式启用时，后端接收全部邮件和 HTTP origin 参数，scheduler 使用同一应用镜像、调用 `send_daily_summaries` 并由 Jenkins 按启用标志控制 profile；HTTP IP 来源保持 `http://`，SSL 重定向关闭、HSTS 为 0、session/CSRF secure cookie 关闭。
- 实际行为：5 个断言连续两次全部失败：缺失两项必需密钥时 `docker compose config --quiet` 仍成功；无 SMTP 时没有处于非活动 profile 的 scheduler；SMTP/HTTP 参数没有按公开约定传递到后端；没有启用邮件后的 scheduler profile、调度命令和 Jenkins profile 控制；HTTP IP、SSL redirect、HSTS 和 secure cookie 组合未配置。失败为 Compose/Jenkins 对外配置行为缺失，不是语法或环境错误。
- 是否稳定复现：是；同一脚本、远端 Compose 版本及隔离合成变量下连续两次得到完全相同的 5 项失败。脚本显式 unset SSH 远端进程可能继承的相同变量，未读取或依赖服务器 `.env`。
- 回归结果：没有本机 Docker 可用于本地 Compose；远端只校验临时副本，没有运行 Jenkins 发布、数据库迁移、备份、HTTP health/calendar 冒烟、容器状态变更或真实 SMTP 连接。
- 覆盖的验收标准：缺失必需密钥保护、邮件未配置时 scheduler 关闭、SMTP 变量与启用 profile 传递、HTTP IP 不强制 HTTPS。
- 未覆盖风险：Jenkins `release` 分支选择、备份权限及保留、迁移和发布后 health/API/UI 冒烟尚未执行；SMTP 实际服务商连通和真实收件箱投递未执行。后续实现复测须继续使用无敏感值的合成 env。
- 黑盒声明：只读取公开 `docker-compose.yml` 与 `Jenkinsfile` 的副本并观察远端 Compose 配置输出；从未打开、读取、复制或打印 `/root/job/.env`，没有输出真实 SMTP 密码或 SSH 凭据，也未读取应用生产源码。
