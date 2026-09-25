# WEB-APP-005 实现说明

- 状态：`READY_FOR_TEST`
- 修改范围：`frontend/src/components/ApplicationForm.vue`、`frontend/src/api/applications.ts`、`frontend/src/types/application.ts`
- 已实现行为：新增和编辑投递表单为 AI 面、笔试、一面、二面、三面、HR 面分别显示分钟时长输入。无阶段时间时输入为空且禁用；设置新时间后默认 60 分钟；清空时间时同步清空并禁用时长。编辑时回填 API 返回的真实时长；旧记录有时间但响应无时长时按 60 分钟兼容。时长接受 1～1440 的整数，非法值显示对应字段错误并阻止提交；后端 snake_case 时长错误映射到对应控件，服务端和网络错误保留输入。新增请求将时长转换为整数；编辑 PATCH 只包含变化字段，阶段开始时间变化时同时明确提交配对时长。时长字段已加入 API snake_case 映射与投递类型。表单标注阶段时间按浏览器本地时区填写，日历按北京时间显示。
- 数据库迁移：无；由已完成的 APP-008 负责。
- 配置变化：无。
- 已知限制：无。
- 环境：Windows；切换前 nvm 当前版本 / Node.js 均为 `v20.19.0`，npm `10.8.2`；按 `.nvmrc` 执行 `nvm install 20.19.0`、`nvm use 20.19.0` 后，Node.js `v20.19.0`、npm `10.8.2`。依赖已由本任务 RED 阶段按锁文件同步，本次未改变依赖。
- 自检结果：`npm run test -- tests/test_web_app_005.spec.ts tests/test_web_app_003.spec.ts --reporter=dot`：2 个测试文件、19 项通过；`npm run lint`：通过。以上均为实现 Agent 自检，不能替代测试 Agent 独立复测。
- 建议复测命令：在 `frontend/` 且使用 `.nvmrc` 指定的 Node.js 版本运行 `npm run test -- tests/test_web_app_005.spec.ts tests/test_web_app_003.spec.ts --reporter=dot`。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：`WEB-APP-005`
- 当前状态：`READY_FOR_TEST`（任务单状态请项目管理 Agent 更新）
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：六阶段时长表单及 API/类型映射实现；本说明记录实现与自检。
- 接收方工作范围：依据 `docs/tasks/WEB-APP-005.md`、CAL-001 第 2 节及 RED 报告独立复测公开 UI/API 交互；不修改生产实现。
- 输入文档：`docs/tasks/WEB-APP-005.md`、`docs/requirements/CAL-001.md` 第 2 节、`docs/test-reports/WEB-APP-005.md`、APP-008 公开契约与通过报告、WEB-APP-003 公开契约。
- 建议命令：本说明中列出的专项测试与 WEB-APP-003 回归命令。
- 结果或风险：专项和原表单回归 19/19 通过，Vue/TypeScript lint 通过。编辑时变更阶段时间会显式提交配对时长，确保已保存的自定义时长清晰保留。
- 本阶段完成条件：测试 Agent 独立复测并提交 `TEST_PASSED` 或 `TEST_FAILED` 报告。
