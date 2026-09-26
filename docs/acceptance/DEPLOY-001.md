# DEPLOY-001 验收记录

- 状态：`DONE`
- 验收角色：项目管理 Agent
- 任务单：`docs/tasks/DEPLOY-001.md`
- 独立测试报告：`docs/test-reports/DEPLOY-001-test-passed.md`

## 已通过的配置门禁

- [x] 测试 Agent 独立检查通过，7/7 项 Compose/Jenkins 配置合同断言通过；HEAD 基线此前为 0/7。
- [x] 必需密钥缺失时拒绝解析；数据库端口不发布；后端端口限制本机访问。
- [x] SMTP 未配置时不启用邮件调度；显式启用时 scheduler 等待 backend 健康，并执行每日摘要命令。
- [x] Jenkins release 来源检查兼容 `BRANCH_NAME`/`GIT_BRANCH`；HTTP IP 不强制 HTTPS，也不启用 HSTS 和 secure cookies。

## 生产发布验收

- [x] 已验收功能提交到 `release`，Jenkins `RecruitmentStatistics-CI-CD` build #11 成功，部署 revision `2db9b15`。
- [x] 发布前数据库备份 `/root/backups/job-20260926T121317Z.dump` 存在，属主 root、权限 `0600`。
- [x] `db`、`backend`、`frontend` 均健康；通知迁移 `0001_initial`、`0002_daily_delivery` 成功应用。
- [x] 服务器公网 HTTP 首页和 `/calendar` 均返回 200；health API 冒烟成功；未认证日历 API 返回预期 401。
- [x] 数据库密码和 Django secret 已轮换为随机值并写入服务器部署 env；该文件不入库，权限为 root 管理、`0640`，Jenkins 执行身份只读。
- [x] `ENABLE_DAILY_EMAILS=false`，生产未创建邮件 scheduler。

## 后续邮件配置

用户尚未提供可用上游 SMTP 主机、认证凭据和获准使用的 From 邮箱。应用已部署，但通知验证/投递和每日摘要邮件保持关闭；提供这些参数后需安全写入服务器 env、启用邮件调度并验证实际投递。

部署与日历功能验收完成。实际 SMTP 投递不在本次完成声明内。
