# WEB-APP-009 RED_CONFIRMED

- 测试角色：独立测试 Agent（release_tests）。
- 环境：Windows；项目 `.nvmrc` Node 20.19.0、npm 10.8.2；锁定前端依赖与本机 Edge；Vite 127.0.0.1:5199。HTTP 认证和列表使用合成夹具，不访问真实账号或数据。
- 命令：在 `frontend/` 执行 `npm run test:sharing -- --config=tests/playwright.web_app_009.config.mts --reporter=json`。
- 通过 / 失败：连续两次均 1 / 2，退出码 1，0 flaky。
- 公开输入：任务单指定的用户附件 PNG，SHA-256 `9C0420FD9643705BD36A1C9E8E5C4D80B5FE100EA5B22492BB1301ABBA610403`；合成用户登录后查看项目侧栏品牌，未登录页检查文档 favicon。
- 期望行为：`rel=icon` 指向同源、200、`image/*` 且浏览器可解码的 Logo，其响应字节与用户附件 SHA-256 一致；侧栏品牌标题左侧显示可见图片，提供非空 alt，可通过 URL 加载且响应字节与用户附件一致，项目名称继续可见。
- 实际行为：合成登录、列表导航和“我的投递进度”品牌标题基线通过；文档中找不到带有效 `href` 的 `rel=icon` 链接；侧栏标题左侧找不到可访问的图片。两项失败都直接对应尚缺失的 Logo 行为，并非夹具、浏览器或语法问题。
- 是否稳定复现：完整套件连续两次固定 1 pass / 2 fail，失败位置及公开 DOM 观察一致。
- 回归结果：本阶段只做先行 RED；收到 `READY_FOR_TEST` 后复测本套件、登录/导航相邻行为，并运行前端构建后检查构建产物的 favicon/Logo URL。WEB-APP-008 的工作区未提交文件未读取、未修改、未纳入本次提交。
- 覆盖的验收标准：用户提供图片的字节身份、开发服务器静态可加载、favicon 绑定、侧栏可访问品牌图与项目标题。生产构建资源与相邻回归留待实现后验证。
- 未覆盖风险：本次 RED 只验证缺失行为；构建后路径和浏览器标签页图像的实物呈现尚待独立复测。
- 黑盒声明：未读取或分析 `frontend/src`、`frontend/public`、`frontend/index.html` 或后端生产实现；只使用任务单、公开 DOM/HTTP 与浏览器图片解码结果。

## Agent 交接

- 任务编号：WEB-APP-009。
- 当前状态：RED_CONFIRMED。
- 发送角色：测试 Agent；接收角色：项目管理 Agent，再交独立实现 Agent。
- 已完成内容与产物：`frontend/tests/test_web_app_009.e2e.spec.ts`、`frontend/tests/playwright.web_app_009.config.mts` 与本报告。
- 实现范围：按任务单仅修改实现角色所有的 Logo 资源、网页图标、AppShell 品牌与实现说明；保持测试目录只读。
