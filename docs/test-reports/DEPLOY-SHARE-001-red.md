# DEPLOY-SHARE-001 RED_CONFIRMED

- 测试角色：share_tests，延续独立测试角色，仅运维公开检查，不新增自动化测试。
- 输入：`docs/tasks/DEPLOY-SHARE-001.md`、`DEPLOY-001.md`；用户已明确授权上线。
- 环境：Windows PowerShell；公网 `http://115.190.240.84:5173`；SSH只读别名 `huoshan`。
- 检查时间：2026-09-28 15:31:58 +08:00。
- 通过/失败：首页、共享URL、health共3项HTTP200基线通过；5个匿名新共享GET均404而非401，部署差异RED成立；推荐配置变量缺失。
- 黑盒声明：仅公开HTTP状态/Content-Type、docker服务状态与单一白名单变量输出；未读取生产实现、完整env、真实凭据、完整构建日志或任何用户记录，未进行生产写操作。

## 公开HTTP证据

通过PowerShell `Invoke-WebRequest -SkipHttpErrorCheck -TimeoutSec 20` 逐一GET，只输出路由、状态、Content-Type和可用错误码，不输出响应正文：

| 路径 | 实际 | 期望与说明 |
|---|---|---|
| `/` | 200 text/html | 服务入口正常 |
| `/sharing` | 200 text/html | SPA兜底本身不能证明共享页已上线 |
| `/api/v1/health/` | 200 application/json | API基线正常 |
| `/api/v1/sharing/me/` | 404 text/html | 发布后应401 JSON |
| `/api/v1/sharing/users/recommendations/` | 404 text/html | 发布后应401 JSON |
| `/api/v1/sharing/requests/` | 404 text/html | 发布后应401 JSON |
| `/api/v1/sharing/connections/` | 404 text/html | 发布后应401 JSON |
| `/api/v1/sharing/users/1/applications/` | 404 text/html | 发布后应401 JSON；匿名检查不访问用户数据 |

失败由当前部署缺少新公开接口导致，不是网络/服务中断、语法、夹具或业务测试环境错误。

## 只读容器证据

`ssh huoshan "docker ps --format '{{.Names}} {{.Status}}'"`：

- job-frontend-1：Up 5 hours（healthy）。
- job-backend-1：Up 7 hours（healthy）。
- job-db-1：Up 7 hours（healthy）。

仅对白名单环境变量执行docker inspect模板：

```text
docker inspect --format '{{range .Config.Env}}{{if eq (index (split . "=") 0) "SHARING_RECOMMENDATION_COUNT"}}{{println .}}{{end}}{{end}}' job-backend-1
```

命令退出0，仅空输出，证明当前容器未传入 `SHARING_RECOMMENDATION_COUNT`；未输出/读取其他环境值。默认10和部署.env可配置透传尚需实现发布。

## 交接

- 当前状态：RED_CONFIRMED；已通知项目管理与实现角色。
- 接收角色：share_implementation，仅按部署任务允许范围修Compose透传并通过现有Jenkins release流水线发布，生产写操作由实现角色完成。
- 发布前已有业务与文案测试均已验收，不重跑全量；RED只证明部署差异。
- 发布后独立复测范围：准确Jenkins revision/SUCCESS、受限非空备份、迁移及头像有效覆盖聚合、容器健康、推荐变量值、公开首页/共享URL/health200、所有匿名共享API401、线上bundle新页面和“申请共享”文案。
- 本次未独立读取Jenkins构建记录，PM提供的既有#14 SUCCESS及远端旧revision仅作为上下文；最终必须独立确认实际发布本次revision。
- 不创建生产账号，不发共享申请，不查看真实个人记录，不触发真实邮件；邮件启用状态需保持原值。
