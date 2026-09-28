# DEPLOY-SHARE-001 实现说明

- 状态：IMPLEMENTING（运行配置已完成，等待PM推送及Jenkins发布证据）
- 实现角色：share_implementation；独立测试角色：share_tests。
- 输入：`docs/tasks/DEPLOY-SHARE-001.md`、RED报告`docs/test-reports/DEPLOY-SHARE-001-red.md`，测试先行提交`04c8bb8`。
- 修改范围：`docker-compose.yml`仅backend增加`SHARING_RECOMMENDATION_COUNT: ${SHARING_RECOMMENDATION_COUNT:-10}`；本说明。业务、SMTP、Jenkins及数据卷未修改。
- 配置变化：生产backend默认10，可由现有部署环境配置1～50；后端既有启动检查拒绝非法值。没有读取或编辑真实部署.env。
- 自检：服务器现有Docker Compose v5.1.0，SSH huoshan；以Python TemporaryDirectory传入本地Compose副本及合成环境变量，`docker compose config --format json`只解析临时配置，不启动服务。仅输出目标变量：未设值10、显式设置3均通过。配置JSON与合成密钥不输出，临时目录自动清理。无需安装依赖或运行uv/nvm/全量业务测试。
- 数据库迁移：待Jenkins发布后核实sharing `0001_initial`、`0002_assign_existing_avatars`，仅由既有容器启动命令执行。旧用户头像仅输出匿名聚合数。
- 发布门禁：仅PM推送release精确HEAD，Jenkins `RecruitmentStatistics-CI-CD` SCM轮询发布；本实现不提前push，不绕过流水线直部署。发布前既有流水线执行root-only非空pg_dump备份。
- 后续证据：待填Jenkins构建编号/SUCCESS/revision、备份owner/mode/size、sharing迁移、容器健康、匿名HTTP状态、推荐配置和头像聚合。
- 已知限制：生产只读检查，不创建账号/申请，不访问个人投递内容；SMTP启用状态保持。当前前端URL200可能只是旧SPA兜底，需新bundle及API401证明实际新功能上线。
- 测试完整性声明：未新增测试或修改测试/断言/门槛，保留全部无关未提交文件；后续READY_FOR_TEST由原测试Agent独立线上复测。
