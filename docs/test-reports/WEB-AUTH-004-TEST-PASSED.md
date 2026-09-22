# WEB-AUTH-004 TEST_PASSED

- 测试角色：测试 Agent
- 环境：Windows；Node.js `v20.19.0`（与 `.nvmrc`、`package.json` 一致）；npm `10.8.2`；Vitest `4.1.11`；Playwright `1.56.1`；Desktop Chrome 项目。
- 命令：
  - `npm run test -- tests/test_web_auth_004.spec.ts tests/test_web_auth_003.spec.ts --reporter=verbose`
  - `npm run dev -- --host 127.0.0.1`
  - `npm run e2e -- tests/e2e/web_auth_004.spec.ts --reporter=list`
  - `npm run test -- tests/test_token_storage.spec.ts tests/test_rel_001_auth_store.spec.ts tests/test_web_auth_002.spec.ts tests/test_web_auth_003.spec.ts tests/test_web_auth_004.spec.ts --reporter=verbose --maxWorkers=1 --no-file-parallelism`
  - 补充诊断：`npm run test -- --reporter=verbose`、`npm run test -- tests/test_web_auth_002.spec.ts --reporter=verbose`、`npm run test -- tests/test_web_app_002.spec.ts --reporter=verbose`
- 通过 / 失败：任务定向与相邻认证组件测试 `10 / 0`；真实浏览器视口与导航测试 `5 / 0`；完整认证相关回归 `33 / 0`。补充完整前端套件首轮为 `66 / 3`，其中认证 Store 超时用例单文件复跑为 `9 / 0`；两个与本任务无关的 `WEB-APP-002` 列表路由用例单文件复跑仍失败，记录为现有非本任务回归风险，不影响本任务相关测试结论。
- 公开输入：分别直接访问 `/login`、`/register`；使用 `1280 × 900` 与 `375 × 812` 浏览器视口；在注册页聚焦可访问名称为“返回登录”的链接并按 `Enter`；监听注册 API 的 `POST /api/v1/auth/register/` 请求。
- 期望行为：桌面端两页认证卡片可见宽度均为 `560px ± 2px` 且一致；375px 窄屏左右各至少保留 `16px`，页面无横向溢出；“返回登录”可见、可聚焦并导航到 `/login`，且不提交注册；既有认证行为保持通过。
- 实际行为：Playwright 中登录与注册卡片在 1280px 视口均落入 `558px` 至 `562px` 允许区间，公开最大宽度为 `560px`；两页在 375px 视口左右间距均不小于 `16px`，文档宽度未超过视口宽度；“返回登录”链接可见且获得焦点，按 `Enter` 后进入 `/login`，注册请求计数为 `0`；任务组件测试和完整认证相关回归全部通过。
- 是否稳定复现：是。组件契约与真实 Chromium 布局分别通过独立测试层验证，认证相关套件在单工作进程下完整通过。
- 回归结果：登录/注册提交、校验、错误展示、注册成功跳转、认证 Store、路由守卫、Token 存储与刷新相关共 `33` 项通过；任务真实浏览器测试 `5` 项通过。完整前端探索性回归暴露 `WEB-APP-002` 两项稳定失败（浏览器前进/后退恢复查询，以及退出后测试路由未变为 `/login`），实现交接声明仅修改登录页与注册页，这两项不属于本任务改动或验收范围，已作为未覆盖风险上报。
- 覆盖的验收标准：1280px 两页卡片 `560px ± 2px` 且一致；375px 两页无横向溢出并保留至少 16px 侧边距；注册页存在可访问、可聚焦的“返回登录”入口；键盘激活后导航 `/login` 且不调用注册 API；既有认证相关行为通过回归。
- 未覆盖风险：真实浏览器像素验证仅运行 Desktop Chrome 项目，未覆盖 Firefox、WebKit、浏览器缩放或超大字体；后端服务未参与本任务布局与本地路由测试。完整前端套件仍有两个独立的 `WEB-APP-002` 失败，需由对应任务单独跟踪；Vitest 中既有空路径路由提示与 Vue Router `next()` 弃用警告未在本任务处理。
- 黑盒声明：未读取或分析生产实现代码。

## 结论

WEB-AUTH-004 的全部公开验收行为及必要认证回归均通过，状态设置为 `TEST_PASSED`，可交给项目管理 Agent 进入验收。
