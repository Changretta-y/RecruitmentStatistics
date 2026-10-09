# APP-013 RED

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；项目 Python 3.11.13；uv 0.7.21；`uv sync --frozen --group test`；本机 `127.0.0.1:55439` 隔离 PostgreSQL 合成测试库。通过 `backend/tests/run-isolated-postgres.ps1` 只对测试子进程注入合成连接和密钥。
- 命令（在 `backend/` 执行）：`& .\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_013.py','--tb=no','-q')`
- 通过 / 失败：APP-013 新增黑盒测试 5 通过、1 失败，共 6 项；退出码 1。目标单项以 `--tb=line -q` 再运行，仍在相同公开响应断言失败。
- 公开输入：用户 A 创建 `recruitment_url: null` 的全局公司并建立私有岗位；用户 B 使用规范化同名公司、旧 flat `position_name` 和有效 `application_url` 发起 POST。边界覆盖已有非空链接、非法 URL、空字符串及未提供 URL。
- 期望行为：B 的 POST 返回 201 并复用 A 的公司 ID；有效旧链接补齐该公司的公开 `recruitment_url`，POST 响应、公司详情和双方各自列表投影一致；岗位和备注仍按用户隔离。已有非空链接不可覆盖，非法 URL 拒绝且不留下投递，空/缺失 URL 不写入公司链接。
- 实际行为：B 的 POST 返回 201 且 `company_id` 正确复用，但响应 `recruitment_url` 为 JSON `null`，而期望 `https://jobs.example.test/campus?from=legacy`。失败位置为 `backend/tests/test_app_013.py:108`，不是登录、数据库、迁移或测试夹具错误。其他 5 项边界测试通过。
- 是否稳定复现：是；整套运行和目标单项复跑均因相同缺失行为失败。
- 回归结果：`& .\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_012.py','--tb=no','-q')` 为 5 通过、0 失败。APP-013 对“已存在但 URL 为空的公司”的补齐规则是对 APP-012 旧 flat 一次性输入条件的新增契约；已有非空链接保护保持不变。
- 覆盖的验收标准：跨用户同名复用与链接补齐、响应/列表/公司详情公开投影、私有岗位隔离、已有非空链接保护、非法 URL 的字段级错误与原子性、空/缺失 URL 不清空链接。
- 未覆盖风险：尚未检验并发提交；测试只通过认证 HTTP API 观察行为，不检查数据库内部结构或真实插件请求。
- 黑盒声明：未读取或分析生产实现代码。

## Agent 交接

- 任务编号：APP-013
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：功能实现 Agent
- 已完成内容与产物：`backend/tests/test_app_013.py` 与本 RED 报告。
- 接收方工作范围：修复后端生产实现及实现说明，不修改测试、断言或测试门槛。
- 输入文档：`docs/tasks/APP-013.md`、`docs/requirements/APP-012.md`、本报告。
- 建议命令：在 `backend/` 运行 `& .\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_013.py','tests/test_app_012.py','--tb=no','-q')`。
- 结果或风险：目标行为稳定 RED，邻近 APP-012 通过；保留跨用户私有投递隔离。
- 本阶段完成条件：实现交 `READY_FOR_TEST` 后由测试 Agent 独立复测。
