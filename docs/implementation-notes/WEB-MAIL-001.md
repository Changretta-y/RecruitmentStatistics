# WEB-MAIL-001 实现说明

- 状态：`READY_FOR_TEST`
- 修改范围：`frontend/src/api/notification-settings.ts`、`frontend/src/router/index.ts`、`frontend/src/views/ApplicationsView.vue`、`frontend/src/views/NotificationSettingsView.vue`、`frontend/src/views/NotificationVerifyView.vue`。
- 已实现行为：投递页顶部提供固定可见的通知设置入口；登录用户可以查看本人邮箱、每日发送时间、启用/验证状态、固定时区“北京时间（Asia/Shanghai）”和最近发送结果。`unknown` 显示“发送结果待核实”。用户可修改邮箱、时间及开关；保存后以 API 返回值为准。修改地址后显示待验证并关闭推送，重新验证前不能开启；若用户在未保存的新地址状态点击发送验证邮件，页面先保存该地址并强制关闭通知，再申请验证邮件，避免向旧地址发送验证链接。
- API：统一认证客户端调用 MAIL-001 的 `GET/PATCH /api/v1/notification-settings/`、`POST /api/v1/notification-settings/verification/` 和 `POST /api/v1/notification-settings/verify/`。表单只提交收件地址、`HH:mm` 时间和启用状态；没有 SMTP 凭据输入或回显。401 交给共享认证刷新/退出流程，字段错误、限流、服务端和网络错误会显示可理解提示，保存失败保留当前草稿；请求不确定时重新拉取服务器状态，但不覆盖编辑中的表单。提交中禁用重复保存/验证请求。
- 验证链接：新增受认证保护的 `/notification-settings/verify` 路由。页面在调用验证 API 前同步移除地址栏中的查询参数，只将令牌放在本次请求体，不写入长期存储。成功与失败均显示结果；无效/过期/已使用令牌、401、服务端和网络错误有各自提示。
- 数据库迁移：无。
- 配置变化：无。所有时间控件和标签明确使用 `Asia/Shanghai`，未采集用户 SMTP 配置。
- 已知限制：真实 SMTP 投递由服务端负责，本任务仅调用公开 API，不连接 SMTP；真实邮箱送达不在本次前端自检范围。验证 API 按 MAIL-001 需要有效登录态。
- 自检结果：Windows；Node.js `v20.19.0`；npm `10.8.2`。由于并行任务可能切换 nvm4w 的共享 junction，本任务进程将 `C:\Users\Yinchengyu\AppData\Local\nvm\v20.19.0` 放在 PATH 首位并确认 `node --version` 为 `v20.19.0`。定向 E2E `npm run e2e -- web_mail_001.spec.ts --reporter=line`：8/8 通过。`npm run lint` 通过；`npm run build` 通过，Vite 输出既有 `configLoader: 'native'` 提示，无构建错误。
- 建议复测命令：在固定 Node 20.19.0 的进程 PATH 下启动 `frontend/` 的 `npm run dev -- --host 127.0.0.1`，再从仓库根目录执行 `npm run e2e -- web_mail_001.spec.ts --reporter=line`；复测后可在 `frontend/` 执行 `npm run lint` 和 `npm run build`。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：`WEB-MAIL-001`
- 当前状态：`READY_FOR_TEST`
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：通知设置 API 客户端、登录后设置页路由和可见导航、本人设置读取/保存、邮箱验证申请和验证落地页面；实现说明见本文。实现自检定向 E2E 8/8、lint 和 build 均通过。
- 接收方工作范围：仅 `frontend/tests/`、`tests/e2e/`、`docs/test-reports/`；生产实现只读。
- 输入文档：`docs/tasks/WEB-MAIL-001.md`、`docs/requirements/CAL-001.md` 第 5、8 节、`docs/tasks/MAIL-001.md`、`docs/test-reports/MAIL-001-passed.md`、`docs/test-reports/WEB-MAIL-001-red.md`。
- 建议命令：Node 20.19.0 固定在当前进程 PATH 后执行 `npm run e2e -- web_mail_001.spec.ts --reporter=line`；有必要时运行 `npm run lint`、`npm run build`。Vite 开发服务地址 `http://127.0.0.1:5173`。
- 结果或风险：自检已覆盖保存/启停、邮箱变更后验证、错误状态与输入保留、请求防重复、验证令牌成功/失败清理、SMTP 凭据不显示；真实 SMTP 不属于前端复测范围，401 沿用共享认证客户端。
- 本阶段完成条件：测试 Agent 按任务单独立复测公开 UI 和 API 交互，补齐通过或失败报告后由项目管理 Agent进入验收或回流。
