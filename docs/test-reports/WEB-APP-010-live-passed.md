# WEB-APP-010 LIVE TEST_PASSED（替换项目 Logo）

- 测试角色：独立测试 Agent（release_tests）。
- 检查日期：2026-10-07，Asia/Shanghai。
- 发布上下文：项目管理 Agent 已确认最终提交 `3f3fe5a` 对应 Jenkins #25 `SUCCESS`；本报告独立核对部署后的公开 HTTP 与容器健康，不将该构建声明当作本角色独立检查结果。
- 环境：Windows PowerShell；匿名访问 `http://115.190.240.84:5173/` 和 `/logo.png`；SSH `huoshan` 只读三个指定容器的状态与健康字段。未登录生产账号、未读取配置或用户数据。
- 通过 / 失败：四组线上只读核对全部通过，0 失败。
- 公开输入：新用户附件期望 SHA-256 `A09C7876116515619AC4A2ED0293ADE91077627A446329458CED6B9515D79E88`。
- 期望行为：首页 HTTP 200 且标题正常，favicon 指向 `/logo.png`；Logo 响应为 PNG 且原始字节匹配新附件；数据库、后端和前端容器均运行且健康。
- 实际行为：首页 HTTP 200，`<title>` 为“校招进度管理系统”，`rel=icon` 的 href 为 `/logo.png`；`/logo.png` HTTP 200、`image/png`、1,242,665 字节，SHA-256 精确等于新附件。`job-db-1`、`job-backend-1`、`job-frontend-1` 均为 `running healthy`。发布前同一公开 Logo 路径曾为旧图 SHA-256 `9C0420FD9643705BD36A1C9E8E5C4D80B5FE100EA5B22492BB1301ABBA610403`，本次已不再是旧图。
- 是否稳定复现：本次部署后四组独立读取均通过；此前本地 `WEB-APP-010-passed.md` 的 Edge 3/3、lint/build 与构建产物新 SHA 证据保留。
- 命令与复现方式：首页和 Logo 使用 PowerShell `Invoke-WebRequest` 匿名 GET；只解析首页标题/图标 href 与 Logo 状态、Content-Type、长度，在内存对响应字节执行 SHA-256。容器使用 `ssh -o BatchMode=yes huoshan` 执行限定三个名字的 `docker inspect --format '{{.Name}} {{.State.Status}} {{.State.Health.Status}}'`，只返回名称、运行状态和健康字段。
- 回归结果：线上首页与前端静态图正常；三个服务容器健康。本次未执行生产用户业务操作，也未触发 Jenkins 构建。
- 覆盖的验收标准：线上新 Logo 字节、favicon 路径、首页可访问与运行环境健康；本地 AppShell alt、登录导航和构建由前述本地通过报告覆盖。
- 未覆盖风险：未核对 CDN 或其他缓存层，也未验证真实用户浏览器缓存刷新；当前直接公开入口返回的是新图。
- 黑盒声明：未读取或分析生产实现、真实环境变量、个人数据、构建日志或完整 Jenkins XML；未 push、未触发构建、未更改服务器。

## Agent 交接

- 任务编号：WEB-APP-010（换 Logo）。
- 当前状态：线上 TEST_PASSED。
- 发送角色：测试 Agent；接收角色：项目管理 Agent。
- 已完成内容与产物：部署后匿名 HTTP 和容器健康独立证据、本报告。
- 接收方工作范围：据本地与线上测试报告完成发布验收。
