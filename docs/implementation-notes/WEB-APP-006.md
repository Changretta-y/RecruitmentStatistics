# WEB-APP-006 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/src/api/applications.ts`、`frontend/src/types/application.ts`、`frontend/src/utils/company-application.ts`、`frontend/src/components/ApplicationForm.vue`、`frontend/src/components/PositionFlowCard.vue`、`frontend/src/views/ApplicationFormView.vue`、`frontend/src/views/ApplicationsView.vue`。
- 已实现行为：新增及编辑页以公司为主记录，维护多个岗位及各自投递状态、时间、链接、备注、可重复命名的多条面试；AI 面、测评、笔试各只显示一组公司共享时间和时长。时间用本地日期时间控件填写，提交为 ISO 时间；填写时间后时长默认 60 分钟，清空时间同时清空时长。
- 已实现行为：首页一家公司一行，单岗位流程直接可见，多岗位可通过键盘操作的按钮展开全部岗位及其面试，共享流程只出现一次；窄屏岗位详情纵向排布。既有搜索、筛选、排序、分页及旧 flat API 调用保留兼容读取与字段映射。
- 已实现行为：编辑仅 PATCH 实际修改的字段与目标对象 ID，再逐项 DELETE 明确移除的面试和岗位；PATCH 成功即采纳服务端新 ID，删除成功即移出待处理队列。部分删除失败保留表单、已保存的新 ID 和待删队列，后续重试只发送剩余改动；未完成队列仍触发离开确认。保存期间禁用输入、结构操作及重复提交；服务端嵌套字段错误映射至对应输入。删除公司失败后确认框保留错误提示和重试按钮。
- 数据库迁移：无；依赖已完成的 APP-009 后端嵌套 API。
- 配置变化：无；本机集成使用现有 `VITE_API_PROXY_TARGET=http://127.0.0.1:8019`。
- 已知限制：一次编辑由原子 PATCH 与逐项 DELETE 组成；跨请求不具备整体事务，部分失败按上述队列机制明确提示并可继续修改重试。真实 API 合成账号集成暂受本机隔离 PostgreSQL 数据目录失效影响，须在环境恢复后由独立测试角色复测，不视为生产实现失败。
- 自检结果：Node 20.19.0 下 `npm run lint`、`npm run build` 均通过；WEB-APP-006 不依赖真实数据库的 Edge 黑盒 11/11 通过；`npm run test -- tests/test_web_app_003.spec.ts tests/test_web_app_005.spec.ts` 为 19/19 通过；`git diff --check -- frontend/src` 通过。此前完整旧组件集有部分旧固定流程及 dialog 选择器断言待测试角色按公开契约适配，不能据此宣称全项目全绿。
- 建议复测命令：`npm run test:sharing -- --config=tests/playwright.web_app_006.config.mts --reporter=line`；`npm run test -- tests/test_web_app_003.spec.ts tests/test_web_app_005.spec.ts`；`npm run lint`；`npm run build`。
- 测试完整性声明：未修改测试、断言或质量门槛。
