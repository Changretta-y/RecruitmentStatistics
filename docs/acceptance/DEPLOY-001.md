# DEPLOY-001 验收记录

- 状态：`ACCEPTING`
- 验收角色：项目管理 Agent
- 任务单：`docs/tasks/DEPLOY-001.md`
- 独立测试报告：`docs/test-reports/DEPLOY-001-test-passed.md`

## 已通过的配置门禁

- [x] 测试 Agent 独立检查通过，7/7 项 Compose/Jenkins 配置合同断言通过；HEAD 基线此前为 0/7。
- [x] 必需密钥缺失时拒绝解析；数据库端口不发布；后端端口限制本机访问。
- [x] SMTP 未配置时不启用邮件调度；显式启用时 scheduler 等待 backend 健康，并执行每日摘要命令。
- [x] Jenkins release 来源检查兼容 `BRANCH_NAME`/`GIT_BRANCH`；HTTP IP 不强制 HTTPS，也不启用 HSTS 和 secure cookies。

## 尚待完成的生产验收

- [ ] 将已验收功能提交到 `release` 并经 Jenkins 流水线部署。
- [ ] 确认备份文件及权限、生产容器状态、数据库迁移和线上首页/health/日历冒烟。
- [ ] SMTP 参数未提供。本次保持 `ENABLE_DAILY_EMAILS=false`；真实邮箱验证和收件投递不作为本次验收通过项。

只有上述生产部署与 HTTP 冒烟通过后，才把任务更新为 `DONE`。邮件调度需在后续配置上游 SMTP 后另行验证。
