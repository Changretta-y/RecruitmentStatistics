# APP-014 / WEB-APP-014 实现说明

- 状态：READY_FOR_TEST
- 修改范围：新增 `backend/apps/prompts` 提示词模型、迁移、序列化、分页和用户隔离 API；注册后端路由与应用；新增前端提示词 API、受保护 `/prompts` 页面、路由和 AppShell 导航。
- 已实现行为：认证用户首次访问列表时原子创建三类预设（自我介绍、项目经历深挖、行为面试 STAR），通过初始化标记保证用户删除预设后刷新不会重建；列表按当前用户隔离并支持标题/内容不区分大小写搜索和分页 envelope；新增、局部编辑、删除、长度/空白校验和越权 404 均由 API 处理。前端提供搜索、预设标识、选择后复制/编辑/删除、新增表单、二次确认和可见成功/错误状态。
- 数据库迁移：新增 `prompts` 与 `prompt_initializations` 表，迁移文件为 `backend/apps/prompts/migrations/0001_initial.py`。
- 配置变化：`backend/config/settings.py` 注册 prompts app；`backend/config/urls.py` 注册 `/api/v1/prompts/`。
- 已知限制：后端专项当前测试文件存在既有夹具问题（用户名前缀与 UUID 拼接后超过注册接口 30 字符限制，且首项对响应的 `results` 采用了错误的 header 下标）；已在交接中保留该证据，待测试 Agent按公开契约独立复测。真实线上数据库未操作。
- 自检环境：Windows；Python 3.11.13、uv 0.7.21；Node.js 20.19.0、npm 10.8.2。
- 自检结果：前端 `npm run lint`、`npm run build` 通过；WEB-APP-014 专项在修正表单/删除对话框后 7/8 通过，剩余 1 项为新增标题与创建对话框标题同名的测试选择器冲突，已将对话框标题改为“提示词表单”，应由下一次运行确认。后端迁移由隔离 runner 执行；APP-014 首次运行暴露上述测试夹具问题，其余 API 行为已可访问。
- 建议复测命令：`backend/tests/run-isolated-postgres.ps1 -Port 55439 -DatabaseName app009_test -PytestArguments @('tests/test_app_014.py','--tb=no','-q')`；在 `frontend` 执行 `npx playwright test --config=tests/playwright.web_app_014.config.mts --reporter=line`。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：APP-014 / WEB-APP-014
- 当前状态：READY_FOR_TEST
- 发送角色：功能实现 Agent
- 接收角色：测试 Agent
- 已完成内容与产物：用户隔离提示词 API、数据库迁移、`/prompts` 页面和主导航入口。
- 接收方工作范围：独立黑盒复测 API 隔离/CRUD/预设生命周期和页面路由、搜索、复制、表单、确认及错误状态。
- 输入文档：`docs/tasks/APP-014.md`、`docs/tasks/WEB-APP-014.md`、对应 RED 报告。
- 结果或风险：前端已完成构建及专项自检；后端公开契约可用，专项测试中的注册用户名长度和响应下标需按测试报告核对。
- 本阶段完成条件：测试 Agent 完成独立复测并提交 TEST_PASSED 或 TEST_FAILED，项目管理 Agent随后验收。
