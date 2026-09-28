# DEPLOY-SHARE-001 TEST_PASSED

- 测试角色：share_tests，原独立运维测试角色；无生产写操作。
- 输入：`docs/tasks/DEPLOY-SHARE-001.md`、`DEPLOY-001.md`、实现说明与READY_FOR_TEST交接（`9bd7d82`，补充命令`9784772`）；发布前RED提交`04c8bb8`。
- 发布目标：release `24d035f9f1c2188f8ed1147ca0f2ff494b3f3eb5`。
- 检查时间：2026-09-28 15:51～15:58 +08:00。
- 环境：Windows PowerShell，通过 `huoshan` SSH现有远端工具进行只读运维；HTTP公网入口 `http://115.190.240.84:5173`。未安装依赖或重跑已验收业务/文案测试。
- 结果：本任务要求的独立上线只读检查全部通过；新API从发布前404变为401 JSON，新页面bundle和新文案均已实际部署。

## 独立发布、备份与容器证据

Jenkins构建保存的元数据仅白名单输出number/result/building/duration_ms/revision：

```text
number=15
result=SUCCESS
building=false
duration_ms=90772
revision=24d035f9f1c2188f8ed1147ca0f2ff494b3f3eb5
```

精确匹配授权release目标。按PM明确允许的方法，以构建metadata作为解析输入，仅输出以上5字段，未拷出/打印原始XML或构建日志；不触发构建、推送或直部署。

`stat --format='%U:%G %a %s %n' /root/backups/job-20260928T073921Z.dump` 独立结果：

```text
root:root 600 58287 /root/backups/job-20260928T073921Z.dump
```

备份非空且仅root可读。备份由既有流水线执行，本测试未打开备份内容。

`docker ps --format '{{.Names}} {{.Status}}'` 独立检查 db/backend/frontend均healthy；后端/前端为本次发布后重新启动，数据库既有运行保留。未见daily-email scheduler容器，与上线前只读服务快照一致；本测试未查看或修改SMTP值。

## 推荐配置、迁移与头像聚合

仅白名单docker inspect模板输出：

```text
SHARING_RECOMMENDATION_COUNT=10
```

发布前同模板无变量输出，现已透传。默认10/合成环境显式配置3的Compose解析证明来自已交接实现自检；线上独立检查只确认目标变量10，不读取真实.env或其他环境值，不改生产配置试验。

只读公共管理命令 `docker exec job-backend-1 uv run --no-sync python manage.py showmigrations sharing` 独立结果：

```text
sharing
 [X] 0001_initial
 [X] 0002_assign_existing_avatars
```

独立只读SQL仅聚合，不选择个人字段/投递记录：

```sql
SELECT (SELECT count(*) FROM auth_user) AS users,
       count(*) AS profiles,
       count(*) FILTER (WHERE avatar IN (
           'avatar-01','avatar-02','avatar-03','avatar-04',
           'avatar-05','avatar-06','avatar-07','avatar-08'
       )) AS valid_avatars
FROM sharing_sharingprofile;
```

通过已有数据库容器psql只打印匿名计数：**3|3|3**，用户/头像profile/8键有效头像数量一致。

## 公网HTTP与bundle

PowerShell `Invoke-WebRequest -SkipHttpErrorCheck -TimeoutSec 20`，仅记录路径、status、Content-Type与错误code；无登录/Token/真实用户操作：

| 路径 | 状态 | 类型/错误 |
|---|---|---|
| `/` | 200 | text/html |
| `/sharing` | 200 | text/html |
| `/api/v1/health/` | 200 | application/json |
| `/api/v1/sharing/me/` | 401 | application/json，UNAUTHORIZED |
| `/api/v1/sharing/users/recommendations/` | 401 | application/json，UNAUTHORIZED |
| `/api/v1/sharing/users/1/` | 401 | application/json，UNAUTHORIZED |
| `/api/v1/sharing/requests/` | 401 | application/json，UNAUTHORIZED |
| `/api/v1/sharing/connections/` | 401 | application/json，UNAUTHORIZED |
| `/api/v1/sharing/users/1/applications/` | 401 | application/json，UNAUTHORIZED |

共享URL的公开脚本 `/assets/index-CvCCjCUQ.js` HTTP200；仅做短语/路径布尔检查，独立观察：

- 包含“申请共享”：true。
- 包含旧“申请互看”：false。
- 包含“投递共享”：true。
- 包含共享API路径 `/sharing/`：true。

页面200、实际新bundle与后端新接口401共同证明本次功能已部署；页面200本身未被当成充分证据。

## 角色边界、风险与交接

- 黑盒声明：未读取/分析生产实现代码，未读取真实.env/完整环境值/密钥，未打印原始Jenkins XML或完整日志，未查看真实用户行/投递记录。只有单变量、服务状态、构建白名单和匿名COUNT输出。
- 未创建生产账号、登录生产用户、发共享申请、接受/拒绝/解除真实共享、触发真实邮件或生产写请求；已验收的本地双用户授权与页面行为证据不由线上匿名冒烟替代。
- 因禁止生产用户写操作，线上POST回应与DELETE解除不实际执行；本地SHARE-001专项41项、页面与18项文案回归的既有验收证据保留。本次只验证发布差异和运行状态，不宣称执行所有认证业务流程。
- 本次未修改业务、测试断言、Jenkins配置或生产环境；无关工作区修改保留；报告本地定点提交，不push。
- 当前状态：TEST_PASSED。接收方项目管理按部署任务单验收并决定DONE；后续文档证据提交无须再次部署。
