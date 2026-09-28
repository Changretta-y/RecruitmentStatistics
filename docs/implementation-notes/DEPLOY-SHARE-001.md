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
- 线上 JS bundle 检查：1 个脚本包，“申请共享”出现 1 次，“申请互看”出现 0 次，共享 API 路径出现 5 次。
- 只读检查通过；未触发构建/部署、未改服务器、未创建生产账号或共享申请、未读取真实投递数据/个人字段/完整 env/密钥/完整日志。
- 远端检查环境：Python 3.11.16、uv 0.9.30；未执行依赖安装或本地构建。
- 独立复测范围与安全边界见 `docs/test-reports/DEPLOY-SHARE-001-red.md`。建议测试 Agent基于本节证据独立复查 release revision、备份元数据、迁移/env/头像聚合、健康状态、匿名 API 与线上文案。

## 独立复测用安全命令

以下均通过 PowerShell 执行 `ssh huoshan '<remote command>'`。命令只输出下列白名单摘要，不输出响应正文、个人字段、真实 `.env`、凭据或完整 Jenkins XML/log。匿名 HTTP 结果可含 URL path、状态码和 Content-Type；头像 SQL 只返回聚合数量。

```powershell
# Jenkins #15：匿名 REST API 返回 403；grep 仅投影 result/SHA/时间标签匹配与 completed 状态，不输出 XML 原文。
ssh huoshan 'docker exec jenkins sh -lc "grep -oE \\"<result>[^<]*|<sha1>[[:xdigit:]]{40}</sha1>|<timestamp>[0-9]+</timestamp>|<duration>[0-9]+</duration>\\" /var/jenkins_home/jobs/RecruitmentStatistics-CI-CD/builds/15/build.xml; test -f /var/jenkins_home/jobs/RecruitmentStatistics-CI-CD/builds/15/workflow-completed/flowNodeStore.xml && echo building=false"'
# Pipeline stage 名称从已完成的 FlowNodeStore 白名单提取；SUCCESS 是该构建的总体结果。
ssh huoshan 'docker exec jenkins sh -lc "grep -oE \\"Validate release source|Validate build tools|Build release images|Backup production database|Deploy production|Smoke test|Declarative: Post Actions\\" /var/jenkins_home/jobs/RecruitmentStatistics-CI-CD/builds/15/workflow-completed/flowNodeStore.xml | sort -u"'
# 最新备份只读元数据。
ssh huoshan 'latest=$(ls -t /root/backups/* 2>/dev/null | head -n 1); test -n "$latest" && stat -c "%n|%U:%G|%a|%s" "$latest"'
# 迁移状态只列共享 app 的 migration 名称/是否已应用。
ssh huoshan 'docker exec job-backend-1 /usr/local/bin/uv run --project /app/backend --no-sync python manage.py showmigrations sharing'
# 唯一目标环境字段；不读取或打印其他容器环境变量。
ssh huoshan 'docker inspect --format "{{range .Config.Env}}{{if eq (index (split . \"=\") 0) \"SHARING_RECOMMENDATION_COUNT\"}}{{println .}}{{end}}{{end}}" job-backend-1'
# 只读 SQL：sharing_sharingprofile.avatar；只返回总配置数和合法头像数，不选择/打印行数据。
ssh huoshan 'docker exec job-backend-1 /usr/local/bin/uv run --project /app/backend --no-sync python manage.py shell -c "from django.db import connection; from backend.apps.sharing.models import AVATARS; marks=\",\".join([\"%s\"]*len(AVATARS)); sql=\"SELECT COUNT(*), COUNT(*) FILTER (WHERE avatar IN (\"+marks+\")) FROM sharing_sharingprofile\"; c=connection.cursor(); c.execute(sql,list(AVATARS)); total,valid=c.fetchone(); print(f\"avatar_aggregate profiles={total} valid={valid}\")"'
# 容器健康状态，不显示环境变量或配置。
ssh huoshan 'docker inspect --format "{{.Name}} {{.State.Health.Status}}" job-db-1 job-backend-1 job-frontend-1'
# 生产 HTTP 元数据。响应体直接丢弃；API host 与生产 smoke 一致。
ssh huoshan 'for path in / /sharing /api/v1/health/ /api/v1/sharing/me/ /api/v1/sharing/users/recommendations/ /api/v1/sharing/requests/ /api/v1/sharing/connections/ /api/v1/sharing/users/1/applications/; do case "$path" in /api/*) host="-H Host:115.190.240.84";; *) host="";; esac; result=$(curl -sS --max-time 20 -o /dev/null -w "%{http_code}|%{content_type}" $host "http://127.0.0.1:5173$path"); printf "%s|%s\\n" "$path" "$result"; done'
# Bundle 扫描仅打印计数与目标文案/API 路径存在性，不输出 JS 内容。
ssh huoshan 'python3 -c "import re,json,urllib.request; base=\"http://127.0.0.1:5173\"; html=urllib.request.urlopen(base+\"/sharing\",timeout=20).read().decode(\"utf-8\",\"ignore\"); srcs=re.findall(r\"<script[^>]+src=[\\\"]([^\\\"]+\\.js)[\\\"]\",html); urls=[s if s.startswith(\"http\") else base+s for s in srcs]; js=[urllib.request.urlopen(u,timeout=20).read().decode(\"utf-8\",\"ignore\") for u in urls]; bundle=\"\\n\".join(js); print(json.dumps({\"script_count\":len(js),\"sharing_label_count\":bundle.count(\"申请共享\"),\"old_label_count\":bundle.count(\"申请互看\"),\"sharing_api_count\":bundle.count(\"/api/v1/sharing/\")},separators=(\",\",\":\")))"'
```

已执行头像 SQL 的计数结果为 `profiles=3 valid=3`（模型 app label `sharing`，表 `sharing_sharingprofile`，字段 `avatar`）；构建元数据结果为 `#15 SUCCESS building=false revision=24d035f9f1c2188f8ed1147ca0f2ff494b3f3eb5`，线上 bundle 计数为 `申请共享=1 申请互看=0 sharing API=5`。StageStore 只证实六个 release 阶段及 post 阶段节点存在；各阶段状态以流水线整体 `SUCCESS` 为准。Jenkins 未认证 REST API 返回 403，故测试角色可以用以上本地只读投影独立复核，不应读取 XML/log 原文。
