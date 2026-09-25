# WEB-MAIL-001 TEST_PASSED 每日邮件通知设置页面

- 测试角色：测试 Agent
- 环境：Windows；Node.js `v20.19.0`；npm `10.8.2`；Playwright `1.63.0`；Vitest `4.1.11`。依据 `.nvmrc` 使用 nvm 选择 Node 20.19.0，并将该已安装版本目录 `C:\Users\Yinchengyu\AppData\Local\nvm\v20.19.0` 置于本次 PowerShell 进程 PATH 首位，确保 npm 与 Playwright 在 Node 20.19.0 下运行。`frontend/npm ci` 退出码 0；npm 对锁文件中的 `abbrev`、`nopt` 报 Node 22 引擎范围警告，安装完整。
- 命令：启动 `frontend/` 的 `npm run dev -- --host 127.0.0.1`；仓库根目录运行 `npm run e2e -- web_mail_001.spec.ts --reporter=line` 和 `npm run e2e -- web_auth_004.spec.ts --reporter=line`；`frontend/` 运行 `npm run test -- --reporter=dot`。应用回归定向运行 `npm run test -- tests/test_web_app_002.spec.ts tests/test_web_app_004.spec.ts tests/test_web_auth_002.spec.ts --reporter=dot`，之后按交接要求再运行一次相同命令确认结果。
- 通过 / 失败：WEB-MAIL-001 专项 `8 / 0`；WEB-AUTH-004 浏览器回归 `5 / 0`；全量 Vitest `109 / 4`（15 个测试文件、113 项）；相邻应用回归定向复跑 `21 / 3`，第二次同样 `21 / 3`。
- 公开输入：登录页面输入模拟用户名和密码；浏览器通过 route mock 模拟 MAIL-001 公开登录、本人通知设置、验证申请及令牌确认 API，覆盖有效和待验证邮箱、`HH:mm` 时间、启停状态、`Asia/Shanghai` 时区及 `last_delivery.unknown`。
- 期望行为：显示本人设置、固定北京时间及最近发送状态；修改邮箱使其待验证并关闭通知，验证邮件只向当前待验证地址申请；合法设置可启停且保存后保持；资料未完整或未验证时不能开启；页面不出现 SMTP 凭据；错误输入、限流、未认证、服务端和网络失败有清楚反馈并保留草稿；验证 token 在成功和失败路径都从地址栏清除；提交期间防止重复请求。
- 实际行为：WEB-MAIL-001 的 8 项原 RED 用例全部通过，包含导航和本人设置展示、`HH:mm` 时间和北京时间标注、`unknown` 的“发送结果待核实”、邮箱变更/旧地址停用提醒/未验证与关闭状态、验证申请、关闭推送后保存、SMTP 凭据不可见、验证成功与失败的 token 清除、400/429/401/503/网络失败反馈及草稿保留、防重复提交。WEB-AUTH-004 的登录/注册页面布局与返回登录交互 5 项全部通过。
- 是否稳定复现：WEB-MAIL-001 专项及 WEB-AUTH-004 浏览器回归在固定 Node/npm 环境下通过；WEB-MAIL-001 页面 API 按公开接口响应模拟，不连接真实 SMTP。
- 回归结果：全量 Vitest 中 109 项通过；3 项 WEB-APP-002/004 断言在此前应用验收记录中已作为既有问题记录，项目管理 Agent 确认为与本任务无关。它们在两次定向复跑中仍复现：后退导航后的搜索值未恢复、登出后路由未转至 `/login`、重置筛选未从 URL 移除 `search`。WEB-AUTH-002 曾在全量运行中出现一次 5 秒超时，但在两次应用回归定向运行中通过。认证浏览器回归通过。
- 覆盖的验收标准：任务单四项验收标准均通过。真实平台 SMTP 连接与收件人投递不属于前端任务范围；MAIL-001 API 本身已有独立通过报告。
- 未覆盖风险：真实 SMTP 投递与实际邮件收件箱不在本次范围；通知页面调用真实后端的端到端链路由 MAIL-001 API 契约和浏览器 mock 联合覆盖，不替代服务端专项测试。
- 黑盒声明：测试仅操作公开浏览器 UI、模拟公开 API 输入/输出，并核对任务单契约；未读取或分析 `frontend/src/`，未修改测试断言或生产实现。
