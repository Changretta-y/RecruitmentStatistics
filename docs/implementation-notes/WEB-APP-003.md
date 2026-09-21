# WEB-APP-003 实现说明

- 状态：READY_FOR_TEST
- 修改范围：frontend/src/components/ApplicationForm.vue、frontend/src/api/applications.ts、docs/implementation-notes/WEB-APP-003.md
- 已实现行为：
  - 新增共用 ApplicationForm.vue，支持 create/edit 两种模式；新增默认 applied 状态、空公司/岗位/备注和 null 时间字段。
  - 编辑模式从传入 application 创建本地副本，输入和提交不会修改原始列表行。
  - 提供公司、岗位、状态、投递时间、AI 面、笔试、一面、二面、三面、HR 面和备注字段。
  - 时间支持文本键盘输入并接受 ISO 8601；带时区值原样保留，未填写或清空明确转换为 null。
  - 前端拦截空白提交、非法状态和非法时间；后端 VALIDATION_ERROR details 支持 snake_case 到表单字段的错误映射。
  - 提交期间设置 loading 并禁用按钮，阻止重复提交；create 使用 POST 语义，edit 仅提交变化字段（包括清空字段的 null）。
  - 成功后清空本地表单，发出 success/saved/refresh(page=1) 并关闭；失败保留输入值和字段错误。
  - 脏表单关闭前调用确认；组件不直接操作 localStorage。
  - applications API 增加 create 别名，供表单通过统一 API 层提交。
- 数据库迁移：不涉及；本任务为前端共用表单。
- 配置变化：不涉及依赖或测试配置变化。
- 已知限制：表单操作由后续页面任务接入列表抽屉/路由；本组件仅通过公开事件通知关闭、保存和第 1 页刷新。
- 自检结果：
  - nvm use 20.19.0：通过；Node.js v20.19.0。
  - WEB-APP-003：9 passed。
  - 前端全量 Vitest：51 passed，6 个测试文件通过。
  - npm run build：通过。
  - 既有认证和 WEB-APP-001/002 回归通过；认证测试期间仅有测试自建空路由产生的 Vue Router no-match stderr。
- 建议复测命令：在 frontend 目录执行 nvm use 20.19.0、npm ci、npx vitest run tests/test_web_app_003.spec.ts --reporter=dot。
- 测试完整性声明：未修改 frontend/tests、测试断言、测试报告、任务单或后端文件。

