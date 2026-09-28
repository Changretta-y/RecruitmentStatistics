# DEPLOY-SHARE-001 实现说明

- 状态：READY_FOR_TEST（运行配置及发布只读检查完成，等待独立线上复测）
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

## 实际发布检查（2026-09-28）

- Jenkins `RecruitmentStatistics-CI-CD` 最近构建：#15，`SUCCESS`，已完成；构建保存的 Git SHA 为 `24d035f9f1c2188f8ed1147ca0f2ff494b3f3eb5`，与授权发布 revision 完全一致。仅按白名单解析构建元数据，未读完整 `build.xml` 或日志。可见阶段摘要：Validate release source、Validate build tools、Build release images、Backup production database、Deploy production、Smoke test、Declarative: Post Actions。
- 最新数据库备份：`/root/backups/job-20260928T073921Z.dump`，owner `root:root`，mode `0600`，大小 `58287` bytes。
- 后端 `showmigrations sharing`：`0001_initial`、`0002_assign_existing_avatars` 均已应用。
- 后端仅目标环境变量：`SHARING_RECOMMENDATION_COUNT=10`。
- 头像只读聚合查询：用户总量 3、共享资料量 3、有效头像量 3；未读取或输出任何用户字段/记录。
- `db`、`backend`、`frontend` 均为 `healthy`。生产入口首页、`/sharing`、health 均返回 200；五个匿名共享 GET（me、recommendations、requests、connections、user applications）均为 `401 application/json`。
- 线上 JS bundle 检查：发现 1 个脚本包，包含“申请共享”，不包含旧“申请互看”文案，并包含共享 API 路径。
- 只读检查通过；未触发构建/部署、未改服务器、未创建生产账号或共享申请、未读取真实投递数据/个人字段/完整 env/密钥/完整日志。
- 远端检查环境：Python 3.11.16、uv 0.9.30；未执行依赖安装或本地构建。
- 独立复测范围与安全边界见 `docs/test-reports/DEPLOY-SHARE-001-red.md`。建议测试 Agent基于本节证据独立复查 release revision、备份元数据、迁移/env/头像聚合、健康状态、匿名 API 与线上文案。
