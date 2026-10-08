# WEB-APP-013 RED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；Node.js 20.19.0（项目 `.nvmrc`）；npm 10.8.2；Playwright Desktop Edge；前端 Vite 测试服务器 `127.0.0.1:5193`，公开 HTTP 请求由测试替身提供。
- 命令（在 `frontend/` 执行）：`npm exec -- playwright test --config=tests/playwright.web_app_013.config.mts`
- 通过 / 失败：新专项 5 通过、3 失败，共 8 项；退出码 1。失败均是公开 UI 行为断言，登录、HTTP 替身、页面加载和测试执行均正常。
- 公开输入：合法 HTTPS 招聘地址、无地址、非 HTTP(S) 地址三条公司记录；4 条公司关键字建议；输入框聚焦、外部点击、内部点击、Escape、建议选择与重试。
- 期望行为：合法地址以公司名作为唯一可见链接文本并在新窗口打开；无效或缺失地址显示普通公司名；建议浮层四个选项完整可见且可点击；页面外部点击关闭浮层。
- 实际行为：合法地址的公司名链接不存在；建议第 3、4 项中心点被查询卡片裁剪，命中结果为 `[true, true, false, false]`；点击浮层外后 `listbox` 仍可见。无地址和非法地址普通文本、Escape、选择后一次查询以及浮层内部重试均通过。
- 是否稳定复现：是。三项失败在完整专项复跑中重现；浮层裁剪还经过单项复跑，行为一致。不是环境或夹具错误。
- 回归结果：`npm exec -- playwright test --config=tests/playwright.web_app_008.config.mts` 为 3 通过、0 失败；更新的 APP-012 公司链接公开契约单项测试（`--config=tests/playwright.web_app_012.config.mts --grep 'company name is the sole website link'`）为 1 失败，缺少公司名链接，与 WEB-APP-013 的 RED 一致。APP-012 原测试中“URL 文本可见一次”的旧断言按本任务新契约改为“公司名为链接、URL 文本不可见”；展开后岗位和编辑入口断言保持。
- 覆盖的验收标准：公司链接文本和新窗口属性、无 URL / 非 HTTP(S) URL、建议项跨卡片可命中、外部关闭、内部输入/建议选择/重试、Escape、单次搜索提交；WEB-APP-008 既有建议回归。
- 未覆盖风险：未连接真实后端或访问真实招聘站点；公开 HTTP 替身仅验证浏览器呈现与交互。
- 黑盒声明：未读取或分析生产实现代码。

## Agent 交接

- 任务编号：WEB-APP-013
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：功能实现 Agent
- 已完成内容与产物：`frontend/tests/test_web_app_013.e2e.spec.ts`、`frontend/tests/playwright.web_app_013.config.mts`、APP-012 受新契约影响的测试更新及本报告。
- 接收方工作范围：仅前端生产实现和实现说明；保持测试、断言和质量门槛不变。
- 输入文档：`docs/tasks/WEB-APP-013.md`
- 建议命令：在 `frontend/` 执行 `npm exec -- playwright test --config=tests/playwright.web_app_013.config.mts`，再运行 WEB-APP-008 与 APP-012 回归。
- 结果或风险：3 项目标行为缺失且稳定复现；5 项相邻行为通过。
- 本阶段完成条件：实现修复后交 `READY_FOR_TEST`，由测试 Agent 独立复测。
