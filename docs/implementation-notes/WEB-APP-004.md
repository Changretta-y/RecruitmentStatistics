# WEB-APP-004 实现说明

- 状态：READY_FOR_TEST
- 修改范围：frontend/src/views/ApplicationsView.vue、frontend/src/api/applications.ts、docs/implementation-notes/WEB-APP-004.md
- 已实现行为：
  - 列表每条记录提供带公司/岗位信息的删除按钮，支持鼠标、键盘 Enter 和屏幕阅读器 aria-label。
  - 删除确认对话框展示公司和岗位；取消或关闭不发起请求，确认调用统一 applications API 的 DELETE 并传递正确记录 ID。
  - 删除成功后刷新当前查询；当前页只剩最后一条且页码大于 1 时回退一页再刷新，并显示删除成功提示。
  - 404 显示记录不存在或已删除并刷新列表；403 显示无权操作；500 显示安全通用错误；网络错误保留当前查询并提供删除重试。
  - 错误提示使用固定安全文案，不展示 token、password 或后端 stack/traceback。
  - 空列表继续提供新增入口，带筛选的无结果状态提供重置筛选操作。
  - applications API 增加 delete 别名，页面仍通过统一 API 层操作，不直接处理 localStorage 或 Token。
- 数据库迁移：不涉及；本任务为前端删除交互。
- 配置变化：不涉及依赖或测试配置变化。
- 已知限制：操作列的编辑/详情入口由后续任务接入；当前删除确认使用原生可访问 HTML 对话框结构。
- 自检结果：
  - nvm use 20.19.0：通过；Node.js v20.19.0。
  - WEB-APP-004：8 passed。
  - 前端全量 Vitest：59 passed，7 个测试文件通过。
  - npm run build：通过。
  - 认证回归期间仅有测试自建空路由产生的 Vue Router no-match stderr，不影响断言。
- 建议复测命令：在 frontend 目录执行 nvm use 20.19.0、npm ci、npx vitest run tests/test_web_app_004.spec.ts --reporter=dot。
- 测试完整性声明：未修改 frontend/tests、测试断言、测试报告、任务单或后端文件。

