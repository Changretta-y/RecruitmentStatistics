# WEB-APP-001 实现说明

- 状态：READY_FOR_TEST
- 修改范围：frontend/src/types/application.ts、frontend/src/api/applications.ts、frontend/src/utils/application-query.ts、frontend/src/utils/query-state.ts、docs/implementation-notes/WEB-APP-001.md
- 已实现行为：
  - 定义 JobApplication、列表分页、统一 API 错误和应用查询状态类型。
  - applications API 统一使用现有 authClient，提供列表、详情、创建、部分更新和删除方法，并提供常用别名。
  - 响应从后端 snake_case 转换为前端 camelCase；请求字段转换回 snake_case。
  - ISO 时间字符串和 null 原样保留，PATCH 使用字段存在性判断，不会因 null 被丢弃。
  - 列表查询支持 page、page_size、search、application_status、stage、application_time_after、application_time_before 和 ordering；空筛选不发送，ordering 保留前导负号。
  - URL 查询状态支持对象与 URL query 双向转换；page 默认 1，pageSize 仅接受 10/20/50/100，非法值回退 20，默认 ordering 为 -updated_at。
  - query-state.ts 提供公开兼容导出，避免调用方依赖具体工具文件名。
- 数据库迁移：不涉及；本任务为前端 API 类型、数据转换和查询状态。
- 配置变化：不涉及新增依赖或配置。
- 已知限制：本任务不实现投递页面 UI、搜索交互组件或后端接口行为。
- 自检结果：
  - nvm use 20.19.0：通过；Node.js v20.19.0。
  - npm ci：通过；npm 输出了既有依赖的 EBADENGINE 警告，但安装成功。
  - WEB-APP-001：12 passed。
  - 前端全量 Vitest：35 passed，4 个测试文件通过。
  - npm run build：通过。
  - 全量认证回归期间仅有测试自建空路由产生的 Vue Router no-match stderr，不影响断言结果。
- 建议复测命令：在 frontend 目录执行 nvm use 20.19.0、npm ci、npx vitest run tests/test_web_app_001.spec.ts --reporter=dot。
- 测试完整性声明：未修改 frontend/tests、测试断言、测试报告、任务单或前端页面以外的后端文件。

