# WEB-APP-010 RED_CONFIRMED（替换项目 Logo）

- 测试角色：独立测试 Agent（release_tests）。
- 环境：Windows；Node 20.19.0、npm 10.8.2、项目锁定依赖、本机 Edge；隔离 Vite 127.0.0.1:5200。线上只读公开静态地址 `http://115.190.240.84:5173/logo.png`，未登录或修改服务器。
- 命令：在 `frontend/` 执行 `npm run test:sharing -- --config=tests/playwright.web_app_010_logo.config.mts --reporter=json`；线上使用匿名 HTTP GET 并在内存计算响应 SHA-256。
- 通过 / 失败：本地 Edge 完整套件连续两次均 **1 / 2**、退出码 1、0 flaky。旧 WEB-APP-009 favicon/侧栏图片两个定向用例仍 2 / 2 通过，确认旧资源基线健康。
- 公开输入：新用户附件 `codex-clipboard-92ab7fb8-e5c5-4b5e-b6c6-ed4781e981d8.png`，期望 SHA-256 `A09C7876116515619AC4A2ED0293ADE91077627A446329458CED6B9515D79E88`；原 Logo SHA-256 `9C0420FD9643705BD36A1C9E8E5C4D80B5FE100EA5B22492BB1301ABBA610403`。
- 期望行为：favicon 和侧栏品牌继续通过 `/logo.png` 加载并保留可访问 alt/标题，但静态资源原始响应字节应替换为新附件；浏览器能解码；登录/导航继续可用。
- 实际行为：合成用户登录、日历/列表导航通过；favicon 的 `rel=icon` 及侧栏图片仍指向 `/logo.png`，但两项资源请求的 SHA-256 都精确等于**旧图**，未达到新图。线上公开 `/logo.png` 只读 GET 返回 HTTP 200、`image/png`、1,040,521 字节，SHA-256 同样精确等于旧图，确认当前线上也尚未替换。
- 是否稳定复现：本地新套件两次固定 1 pass / 2 fail，失败均为旧图字节尚在；原 WEB-APP-009 定向两项通过，排除 favicon、AppShell、Vite 或认证夹具损坏。
- 回归结果：先行阶段只核对当前旧图基线和缺失替换行为。实现 `READY_FOR_TEST` 后复跑本套件并验证构建产物字节、登录/导航和 lint/build；线上新图需随正式发布后再只读核对，不能把本地实现完成等同于线上已更新。
- 覆盖的验收标准：保留 `/logo.png` 绑定、favicon/侧栏原图字节身份、可访问品牌与登录导航；构建及发布后线上核验待后续阶段。
- 未覆盖风险：本次未触发线上发布、未写入生产环境；WEB-APP-008 的未提交工作区改动未读取、修改或纳入本提交。
- 黑盒声明：未读取或分析 `frontend/src`、`frontend/public`、`frontend/index.html` 或后端生产实现；只依据任务单、公开 DOM/HTTP 与响应字节哈希验证。

## Agent 交接

- 任务编号：WEB-APP-010（换 Logo）；同目录既有 `test_web_app_010.e2e.spec.ts` 属 APP-010 状态功能，本任务使用独立 `_logo` 文件名，未覆盖它。
- 当前状态：RED_CONFIRMED。
- 发送角色：测试 Agent；接收角色：项目管理 Agent，再交独立实现 Agent。
- 已完成内容与产物：`frontend/tests/test_web_app_010_logo.e2e.spec.ts`、`frontend/tests/playwright.web_app_010_logo.config.mts` 和本报告。
- 实现范围：按任务单只替换 Logo 资源并写实现说明；测试与 WEB-APP-008 改动保持只读。
