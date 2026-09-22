# WEB-AUTH-004 验收记录

- 状态：`DONE`
- 任务单：`docs/tasks/WEB-AUTH-004.md`
- 测试通过报告：`docs/test-reports/WEB-AUTH-004-TEST-PASSED.md`
- 验收环境：Windows；Node.js `v20.19.0`（与 `.nvmrc` 一致）；Vitest `4.1.11`；Playwright `1.56.1`；Desktop Chrome；Vite 本地服务 `http://127.0.0.1:5173`。

## 标准与证据

- [x] 桌面宽度：项目管理验收运行 `npm run e2e -- tests/e2e/web_auth_004.spec.ts --reporter=list`，1280px 视口下 `/login`、`/register` 的认证卡片均满足 `560px ± 2px`，2 项通过。
- [x] 窄屏布局：同一真实浏览器验收在 375px 视口下确认两页左右边距至少 16px，文档宽度不超过视口宽度，2 项通过。
- [x] 返回入口可访问：注册页存在可访问名称为“返回登录”的链接，可见且可获得键盘焦点。
- [x] 返回行为安全：聚焦链接并按 Enter 后进入 `/login`，监听到的注册 API POST 请求数为 0，1 项通过。
- [x] 认证回归：项目管理验收运行 `npm run test -- tests/test_web_auth_004.spec.ts tests/test_web_auth_003.spec.ts --reporter=verbose`，任务及相邻认证组件测试 10/10 通过；测试 Agent 的完整认证相关回归 33/33 通过。
- [x] TDD 证据完整：存在稳定 `RED_CONFIRMED` 报告、实现说明、独立 `TEST_PASSED` 报告和本验收记录。

## 结论

- 结果：通过。
- 退回角色：无。
- 原因：任务范围内全部公开行为与回归标准均有自动化和真实浏览器证据，项目管理独立验收复跑全部通过。
- 后续动作：将完整前端探索性测试中两个与本任务无关的 `WEB-APP-002` 稳定失败作为独立风险另行处理；本任务不扩展范围。Firefox、WebKit、浏览器缩放和超大字体未纳入本次验收。
