# WEB-APP-014 RED_CONFIRMED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；Node.js 20.19.0（`.nvmrc`）；npm 10.8.2；Playwright 1.63.0；Edge MV3；Vite 隔离开发服务 `127.0.0.1:5194`；合成认证和 HTTP JSON 路由替身。
- 命令：在 `frontend/` 执行 `npx playwright test --config=tests/playwright.web_app_014.config.mts --reporter=line`
- 通过 / 失败：前端专项 `0 passed, 8 failed`，退出码 1；WebServer、合成登录及测试收集均正常。
- 公开输入：匿名访问 `/prompts`；登录后主导航进入 `/prompts`；拦截的提示词分页列表、搜索、创建、PATCH、DELETE 和 503 JSON；公开 DOM、浏览器剪贴板与确认对话框。
- 期望行为：未登录重定向登录；导航出现“提示词管理”；页面展示预设/自定义列表、搜索和空状态；复制成功/失败均有提示；新增/编辑表单校验并刷新；删除二次确认且取消不请求；API 错误可见。
- 实际行为：Vite 路由对 `/prompts` 报 `No match found`；匿名访问未重定向登录；登录后页面没有提示词搜索、预设标题、操作按钮或错误状态。8 项均因缺少公开 `/prompts` 路由/页面行为失败，非 webServer、认证夹具或测试收集错误。
- 是否稳定复现：是。本次单 worker 运行 8 项，WebServer 启动且每项失败位置稳定；失败集中于页面路由/公开控件不存在。
- 回归结果：本阶段仅运行 WEB-APP-014 专项；现有 WEB-APP-010 文件是历史 APP-010 状态 UI 契约，未修改、未纳入本 RED。
- 覆盖的验收标准：路由与登录保护；导航；预设展示和搜索；剪贴板成功/失败；新增、编辑、删除确认；表单校验和网络错误可见。
- 未覆盖风险：真实后端、真实剪贴板权限、移动端专项和生产部署尚未验证；实现后需运行现有投递、日历、通知 UI 回归。
- 黑盒声明：未读取或分析 `frontend/src/`；仅使用公开 URL、DOM、浏览器 API 和拦截的 HTTP JSON。

## Agent 交接

- 任务编号：WEB-APP-014
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：实现 Agent
- 已完成内容与产物：`frontend/tests/test_web_app_014.e2e.spec.ts`、`frontend/tests/playwright.web_app_014.config.mts` 与本报告。
- 接收方工作范围：实现受保护 `/prompts` 页面、导航、搜索、复制、预设、CRUD、确认和可见错误反馈；不得修改测试。
- 输入文档：`docs/tasks/WEB-APP-014.md`、`APP-014` API 契约和本测试文件。
- 建议复测命令：`Set-Location frontend; npx playwright test --config=tests/playwright.web_app_014.config.mts --reporter=line`
- 结果或风险：当前专项 8 项均由缺少 `/prompts` 路由/公开 UI 行为导致失败，环境已排除。
- 本阶段完成条件：实现提交 READY_FOR_TEST 后由测试 Agent 独立复测本专项及现有页面回归。
