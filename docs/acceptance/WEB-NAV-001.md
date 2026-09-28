# WEB-NAV-001 验收记录

- 状态：`DONE`
- 验收角色：项目管理 Agent
- 任务单：`docs/tasks/WEB-NAV-001.md`
- 初始 RED 报告：`docs/test-reports/WEB-NAV-001-red.md`
- 独立通过报告：`docs/test-reports/WEB-NAV-001-passed.md`
- 实现说明：`docs/implementation-notes/WEB-NAV-001.md`
- 验收环境：Windows；Node.js 20.19.0；npm 10.8.2；Playwright 1.63.x；Vitest 4.1.11

## 标准与证据

- [x] 从投递页进入日历后，主侧栏和投递/日历入口可见。Playwright 公开 UI 测试通过。
- [x] 在日历页激活“投递”入口会返回 `/applications` 并显示投递进度标题。独立浏览器测试通过。
- [x] 直接打开 `/calendar` 时侧栏及日历内容仍可见。独立浏览器测试通过。
- [x] 既有日历行为无回归：WEB-CAL-001 专项 11/11 通过；实现 lint 与 build 通过。
- [x] RED 证据稳定命中两种进入日历路径下侧栏缺少投递入口，不是服务、认证或夹具错误。

## 结论

- 结果：通过，状态 `DONE`。
- 退回角色：无。
- 后续动作：无。窄屏仍沿用菜单按钮打开临时抽屉，未在本任务调整。
