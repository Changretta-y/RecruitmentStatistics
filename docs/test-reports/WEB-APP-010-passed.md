# WEB-APP-010 TEST_PASSED（替换项目 Logo）

- 测试角色：独立测试 Agent（release_tests）。
- 环境：Windows；Node 20.19.0、npm 10.8.2、项目锁定依赖、本机 Edge；隔离 Vite 127.0.0.1:5200。认证和列表使用合成 HTTP 夹具。
- 命令与通过 / 失败：在 `frontend/` 运行 `npm run test:sharing -- --config=tests/playwright.web_app_010_logo.config.mts --reporter=json`，**3 / 0**、0 flaky；`npm run lint` 与 `npm run build` 均退出 0。
- 公开输入：用户最新附件 `codex-clipboard-92ab7fb8-e5c5-4b5e-b6c6-ed4781e981d8.png` 的 SHA-256 `A09C7876116515619AC4A2ED0293ADE91077627A446329458CED6B9515D79E88`；favicon 和侧栏公开 URL `/logo.png`。
- 期望行为：原 `/logo.png` 路径、favicon、侧栏 alt/标题与登录导航保持，但资源原始字节换成新附件；构建复制图片而不更改字节。
- 实际行为：favicon `rel=icon` 的 href 精确为 `/logo.png`，开发服务器返回 HTTP 200、`image/png`，浏览器解码成功；侧栏同一路径图片可见且 alt 非空，位于“我的投递进度”标题左侧。两项 HTTP 响应 SHA-256 均精确等于新附件且不再等于旧 Logo SHA。合成登录、日历与投递列表往返导航通过。
- 构建证据：生成的 `dist/index.html` 仍链接 `/logo.png`；`dist/logo.png` 为 1,242,665 字节，SHA-256 精确等于新附件。lint/build 均成功。
- 视觉证据：`G:\job\docs\test-reports\WEB-APP-010-brand.png`，1280×900 Edge 截图；已目视确认新图显示在侧栏项目名左侧、页面布局完整。截屏前仅等待过渡布局稳定，不改变业务断言。
- 是否稳定复现：原 RED 的 favicon 和侧栏字节断言均转绿；最终完整套件 3 / 3、0 flaky。
- 回归结果：登录和导航通过，lint/build 通过；未运行完整前端/后端套件，也未重新测试 APP-010 状态功能。本任务的 `_logo` 测试与其同名旧测试彼此隔离。
- 覆盖的验收标准：新原图字节身份、favicon/侧栏同源可加载、alt 与标题、登录导航、构建后资源字节不变。
- 未覆盖风险：本报告是本地 `READY_FOR_TEST` 独立复测；正式发布后线上 `/logo.png` 的新 SHA 仍需只读核对。WEB-APP-008 工作区未提交改动未修改、未纳入本提交。
- 黑盒声明：未读取或分析 `frontend/src`、`frontend/public`、`frontend/index.html` 或后端生产实现；只使用任务单、公开 DOM/HTTP、浏览器解码与生成的 `dist` 构建产物验证。

## Agent 交接

- 任务编号：WEB-APP-010（换 Logo）。
- 当前状态：TEST_PASSED（本地）；线上资源待项目管理 Agent 发布后独立只读复核。
- 发送角色：测试 Agent；接收角色：项目管理 Agent。
- 已完成内容与产物：原 RED 套件独立复测、构建字节校验、截图与本报告。
- 接收方工作范围：按任务单验收，并安排正式发布后的线上 SHA 核对。
