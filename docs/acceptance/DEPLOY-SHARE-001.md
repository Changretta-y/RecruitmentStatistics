# DEPLOY-SHARE-001 上线验收记录

- 状态：DONE
- 项目管理角色：主 Agent
- 用户请求：继续上线已验收的投递共享与“申请共享”文案。
- 任务单：`docs/tasks/DEPLOY-SHARE-001.md`
- RED：`docs/test-reports/DEPLOY-SHARE-001-red.md`，提交`04c8bb8`
- 业务实现：`4238383`（后端）、`a151234`（前端）、`122ce97`（按钮文案）；运行配置发布提交`24d035f9f1c2188f8ed1147ca0f2ff494b3f3eb5`。
- 独立上线通过：`docs/test-reports/DEPLOY-SHARE-001-passed.md`，提交`46f25c7`。
- 验收入口：`http://115.190.240.84:5173/sharing`

## 标准与证据

- [x] 推荐默认值/生产配置透传：`SHARING_RECOMMENDATION_COUNT=10`；同一Compose映射的合成配置测试默认10、显式3通过。
- [x] 唯一授权发布流程：Jenkins `RecruitmentStatistics-CI-CD` build #15 `SUCCESS`，90.772秒；构建revision精确等于发布目标`24d035f9f1c2188f8ed1147ca0f2ff494b3f3eb5`。
- [x] 迁移与安全备份：sharing `0001_initial`、`0002_assign_existing_avatars`已应用；发布前文件`/root/backups/job-20260928T073921Z.dump`，`root:root`、`0600`、58,287字节。
- [x] 容器健康与匿名头像覆盖：db/backend/frontend均healthy；只读聚合为用户3、头像资料3、有效默认头像3，未输出用户字段。
- [x] 公网行为：主页、`/sharing`、health为HTTP200；六个匿名共享GET均为JSON `401 UNAUTHORIZED`。独立报告另列全部路径、bundle与构建复查证据。
- [x] 前端新版本：生产静态bundle含“申请共享”“投递共享”和sharing API路径，不含旧“申请互看”。本地业务专项及双用户真实流程已先通过独立验收。
- [x] 用户数据与邮件设置：没有在线上创建账号/投递申请、接受/拒绝/解除共享或访问个人投递内容；没有启用SMTP或修改通知配置。

## 结论与范围

全部上线标准通过，任务标记DONE。生产版本已在线。

此前记录的全量前端86/90、既有文档扫描占位误报及旧通知schema提示在各自验收/复测报告保留；本次不宣称全项目全量测试全部通过。该发布只读冒烟不代替本地已有业务角色授权测试，也未实际生产写入个人记录。

无关OPS与WEB-NAV文件保持原有工作区状态，未纳入发布提交。验收文档只写入本地，不再推送或重复发布。
