# DEPLOY-SHARE-001 上线投递共享与申请共享文案

- 状态：TEST_WRITING
- 用户授权：用户明确要求“上线”。
- 用户价值：已验收共享功能和新按钮文案在现有生产入口可用。
- 依赖：SHARE-001、WEB-SHARE-001、WEB-SHARE-002均DONE；沿用DEPLOY-001 Jenkins release唯一发布流程。
- 范围：发布前检查、将推荐数量配置传入部署容器、发布release提交、数据库备份/迁移、独立线上冒烟与最终验收。
- 非范围：修改业务逻辑、启用SMTP、改变Jenkins任务/插件、真实用户授权或申请操作、删除数据、全量旧缺陷修复。
- 角色：根Agent项目管理/发布协调；share_tests独立运维检查与复测；share_implementation运行配置与部署执行。
- 可写范围：PM仅docs/tasks、docs/acceptance；测试仅docs/test-reports（不新增镜像自动化测试）；实现仅docker-compose.yml运行配置、docs/implementation-notes及必要发布操作。保留无关本地未提交文件，不发布它们。

## 公开发布契约

- Jenkins RecruitmentStatistics-CI-CD仅从release发布，通过现有SCM轮询。不得绕过流水线直改生产应用；需要构建记录成功且revision精确匹配本次提交。
- Compose backend传入SHARING_RECOMMENDATION_COUNT，默认10，可由现有部署.env配置1～50；不读取/打印真实.env、密钥、完整日志。
- 发布前root-only数据库备份存在且非空，后端启动自动执行sharing两迁移，不改数据卷。
- 生产首页、/sharing及health均200，所有匿名sharing API为401；构建前当前新API缺失为RED上线差异证据。
- 线上JS bundle包含新共享页与“申请共享”，无旧“申请互看”按钮；共享头像迁移完成，已有用户均有有效头像（仅输出聚合数量、不查看个人记录）。
- 当前邮件启用状态保持；容器db/backend/frontend健康。仅对公开生产入口进行只读冒烟，不新建生产账号、不发共享申请。

## 验收标准

- [ ] 默认10及部署配置透传通过，已验收业务与18项文案回归证据齐全。
- [ ] Jenkins实际发布正确release revision并SUCCESS，备份权限/大小、迁移与容器健康证据齐全。
- [ ] 生产共享页面/API/新文案/已有头像聚合检查通过，独立TEST_PASSED后PM验收。
- [ ] 无关未提交文件保留，未改真实用户共享或SMTP设置。

## 交接

测试Agent先只读preflight确认线上差异/部署配置缺少透传，出RED报告；实现Agent随后只做必要配置和发布，READY_FOR_TEST后交原测试Agent独立线上检查。已通过业务测试无需重跑全量。
