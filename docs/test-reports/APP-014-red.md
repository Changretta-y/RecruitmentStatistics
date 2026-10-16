# APP-014 RED_CONFIRMED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；Python 3.11.13（`.python-version`）；uv 0.7.21；pytest 8.4.2；pytest-django 4.14.0；PostgreSQL 17；独立集群仅监听 127.0.0.1:55439，数据库 `app009_test`，使用合成 DATABASE_URL/DJANGO_SECRET_KEY。
- 命令：`backend/tests/run-isolated-postgres.ps1 -Port 55439 -DatabaseName app009_test -PytestArguments @('tests/test_app_014.py','--tb=no','-q')`
- 通过 / 失败：后端专项 `0 passed, 5 failed, 0 errors`，退出码 1；测试收集、迁移和注册/登录夹具正常。
- 公开输入：两个注册并登录的用户访问 `/api/v1/prompts/`；首次列表、重复列表、搜索、创建、更新、删除、字段边界、客户端 user/owner 字段和越权 ID。
- 期望行为：认证后首次列表创建三类预设且只属于当前用户；返回分页 envelope 和六个公开字段；搜索标题/内容不区分大小写；创建/编辑/删除与长度及空白校验生效；其他用户资源统一 404；预设删除后刷新不重建。
- 实际行为：首个公开断言未认证 `GET /api/v1/prompts/` 收到 HTTP 404（期望 401），说明 `/api/v1/prompts/` 尚未提供；其余用例同样因公开提示词 API 缺失而失败。一次 `-x --tb=short` 复核显示明确为 `Not Found: /api/v1/prompts/`，不是数据库或夹具错误。
- 是否稳定复现：是。独立 PostgreSQL 启动、迁移、Python 环境和认证夹具均成功；专项失败由缺失提示词 API 行为导致。
- 回归结果：本阶段只运行 APP-014 专项；现有同名旧 `test_app_012.py` 属历史公司目录契约，未修改、未纳入本 RED。
- 覆盖的验收标准：首次预设与用户隔离；搜索和分页；新增、修改、删除及校验；越权 404；预设可编辑/删除且不重建；客户端 owner 字段不可注入。
- 未覆盖风险：并发首次访问的竞态需要实现后在隔离库中复测；真实生产数据和公共提示词市场不在范围内。
- 黑盒声明：未读取或分析 `backend/apps/` 或其他生产实现目录；仅通过公开 HTTP API 输入输出测试。

## Agent 交接

- 任务编号：APP-014
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：实现 Agent
- 已完成内容与产物：`backend/tests/test_app_014.py` 与本报告。
- 接收方工作范围：实现 `/api/v1/prompts/` 公开认证 API、预设初始化、隔离、搜索、CRUD、校验和越权契约；不得修改测试。
- 输入文档：`docs/tasks/APP-014.md`、`校招进度管理系统-详细设计方案.md`、本测试文件。
- 建议复测命令：`backend/tests/run-isolated-postgres.ps1 -Port 55439 -DatabaseName app009_test -PytestArguments @('tests/test_app_014.py','--tb=no','-q')`
- 结果或风险：当前后端专项 5 项均因 `/api/v1/prompts/` 缺失而失败；环境已排除。
- 本阶段完成条件：实现提交 READY_FOR_TEST 后由测试 Agent 独立复测本专项及认证/投递相邻回归。
