# WEB-APP-015 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/src/views/PromptsView.vue`。
- 已实现行为：复制优先调用 `navigator.clipboard.writeText`；现代 API 不存在或拒绝时，使用临时只读文本框和 `document.execCommand("copy")` 回退，双重失败才显示失败提示。列表正文按最多 160 个字符生成省略预览；点击卡片打开详情对话框显示完整标题和正文，关闭后恢复折叠列表。详情操作保留复制、编辑和删除流程。
- 自检环境：Node.js 20.19.0、npm 10.8.2、Playwright 1.63.0、Edge。
- 自检结果：`npx playwright test --config=playwright.web_app_015.config.mts --reporter=line` 通过 5/5。WEB-APP-014 中原有“剪贴板拒绝必须失败”的旧场景与本任务公开契约“拒绝后回退成功”行为冲突；未修改测试或加入测试专用分支，需由项目管理/测试阶段按新契约处理回归断言。
- 已知限制：回退复制依赖浏览器允许 `document.execCommand("copy")`；真实浏览器权限和移动端布局仍需验收环境复测。
- 建议复测命令：`Set-Location frontend/tests; npx playwright test --config=playwright.web_app_015.config.mts --reporter=line`，并执行 WEB-APP-014 回归。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：WEB-APP-015
- 当前状态：READY_FOR_TEST
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：复制兼容回退、固定长度预览、详情对话框及本说明。
- 接收方工作范围：独立复测 API 缺失/拒绝/双重失败、长内容预览、详情打开关闭和 WEB-APP-014 其余行为。
- 本阶段完成条件：测试 Agent 提供 TEST_PASSED 或可复现的 TEST_FAILED 报告。
