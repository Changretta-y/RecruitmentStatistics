# REL-SYNC-001 LIVE TEST_PASSED

- 测试角色：release_tests，原独立测试 Agent。
- 检查时间：2026-09-29 11:49–11:54 Asia/Shanghai；最终核对 03:54:15 UTC。
- 发布目标：`884b295501b6338ae51ec528dc39c5f11b841446`。
- 环境：Windows PowerShell 7.6.5、Git 2.46.1.windows.1；现有 SSH `huoshan`、服务器 Python 标准库与 Docker CLI。未安装依赖、未运行生产项目脚本。
- 通过 / 失败：5 组上线只读检查全部通过，0 失败；此前本地先行黑盒 19/0 通过记录保留。
- 公开输入：PM 已通过新入口实际同步的 release SHA、两个远端 refs、Jenkins 构建白名单元数据、公开匿名 HTTP、三个容器健康与备份文件权限/大小。
- 期望与实际行为：GitHub、部署与 Jenkins 构建 revision 完全一致；新构建 SUCCESS/completed；首页与 health 正常；容器 healthy；最新备份 root:root、0600、非空，全部符合任务契约。
- 是否稳定复现：推送后与构建后两次双端 refs、公开 HTTP 均通过；构建最终 SUCCESS 元数据再核对一次仍一致。Jenkins 自动轮询等待约每 50 秒检查，无人工触发。

## 独立只读证据

| 检查组 | 结果 |
| --- | --- |
| 远端 release | origin 与 deploy 均为 `884b295501b6338ae51ec528dc39c5f11b841446` |
| Jenkins | RecruitmentStatistics-CI-CD #16，SUCCESS，completed=true，revision 精确匹配目标 |
| 公开 HTTP | `http://115.190.240.84:5173/` 200；`/api/v1/health/` 200，`{"status":"ok"}` |
| 容器 | job-db-1、job-backend-1、job-frontend-1 均 running healthy |
| 最新备份 | `/root/backups/job-20260929T035316Z.dump`，root:root，0600，71016 字节 |

首次观察仍为旧构建 #15 SUCCESS，revision `24d035f9f1c2188f8ed1147ca0f2ff494b3f3eb5`，因此未当作本次通过。随后自动出现 #16，独立读取白名单为：

```json
{"number":16,"result":"SUCCESS","revision":["884b295501b6338ae51ec528dc39c5f11b841446"],"completed":"true"}
```

## 命令与重现方式

- 远端检查：将 `git remote get-url origin` / `deploy` 的 fetch URL 捕获在变量中，分别执行 `git ls-remote $url refs/heads/release`；只输出远端名称、完整 SHA 与是否匹配，不打印 URL 或凭据。
- HTTP：`Invoke-WebRequest -SkipHttpErrorCheck -TimeoutSec 20` 对上述两个路径执行匿名 GET；首页仅打印状态码，health 仅打印公开响应。
- Jenkins：通过 `ssh -o BatchMode=yes huoshan python3 -` 在远端解析 `/var/lib/docker/volumes/jenkins-data/_data/jobs/RecruitmentStatistics-CI-CD/builds/<最新数字>/build.xml`；只输出 number、result、revision、completed。revision 从 XML 中 sha1/SHA1 元素提取 40 位 hex 并去重；结果仅含本次目标 SHA。未输出或拷出原始 XML、完整日志。
- 容器：远端逐个执行 `docker inspect --format '{{.State.Status}} {{.State.Health.Status}}' <上述容器名>`；只输出运行/健康状态，不读取 Env。
- 备份：远端 Python 对 `/root/backups/job-*.dump` 最新时间命名文件做 stat，仅输出路径、owner、mode、bytes；未打开备份内容。

- 回归结果：本次完整发布路径实际通过；未重新执行已验收业务功能或登录生产账号。
- 未覆盖风险：本次只验证同步与部署健康，未验证长期运行、真实邮件送达或生产用户业务操作。
- 黑盒声明：未读取或分析生产实现；未读取真实 .env、密钥、个人数据、完整 XML 或构建日志；未真实 push、触发构建、修复服务器或变更配置。唯一写入为本地测试报告及其定点提交。

## Agent 交接

- 任务编号：REL-SYNC-001。
- 当前状态：TEST_PASSED（本地行为与独立线上只读证据齐全）。
- 发送角色：原测试 Agent release_tests。
- 接收角色：项目管理 Agent。
- 已完成内容与产物：本地 19/0、RED、本地通过报告、实际双端 refs、Jenkins 精确 revision SUCCESS、线上健康及备份证据。
- 本阶段完成条件：全部通过，交 PM 验收与设置 DONE；本报告定点本地提交不再 push，避免证据文档引发重复部署。
