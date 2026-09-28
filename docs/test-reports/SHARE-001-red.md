# SHARE-001 RED_CONFIRMED

- 测试角色：测试 Agent（share_tests），仅后端任务。
- 环境：Windows PowerShell；Python 3.11.13（根版本声明）；uv 0.7.21；PostgreSQL 本地 127.0.0.1:5432。依赖使用 `uv sync --frozen --group test`；执行使用 `uv run --no-sync` 避免默认同步移除测试依赖。
- 工作目录：`G:/job/backend`。
- 配置：`DATABASE_URL` 使用本地测试 PostgreSQL 数据库，`DJANGO_SECRET_KEY` 使用测试专属至少 32 字符值；不依赖生产配置文件内容。
- 测试文件：`backend/tests/test_share_001.py`（41 个参数化用例）。
- 黑盒声明：未读取、搜索、枚举或分析生产实现代码；仅 HTTP、公开 Django User fixture 和公共管理检查。

## RED 命令与证据

1. `uv run --no-sync pytest tests/test_share_001.py --tb=no -q`
   - 第一批 39 个用例：**0 passed / 39 failed / 0 errors**，82.13 秒。
   - 新端点不存在，获取 me/推荐/申请/共享关系均返回 404；需要 200/201/401/400 的公开行为缺失。
   - 非法推荐配置 0/51/abc/10.5/-1 下公共 `manage.py check` 成功退出，未拒绝启动。
   - 流程用例在首次申请的 404 处失败；注册、登录和已有投递创建均成功，失败来自新行为缺失。
2. `uv run --no-sync pytest tests/test_share_001.py -k 'concurrent or history_keeps or either_party' --tb=no -q`
   - **0 passed / 4 failed / 0 errors / 37 deselected**，16.70 秒。
   - 双方单方解除两个参数化场景重复稳定失败；后来加入的历史上限和真正双线程相反方向并发用例也在缺失新申请行为处失败。

两轮覆盖全部 41 个用例。一次辅助并行启动 pytest 因同名 test 数据库产生 4 个环境 errors，已丢弃，以上第二轮为无 errors 的串行重跑结果；不将环境错误计入 RED。后续不同 Agent 的后端 pytest 应串行运行。

## 独立环境/既有行为基线

`uv run --no-sync pytest tests/test_app_003.py --tb=no -q` → **7 passed / 0 failed**，13.39 秒。

该基线证明原注册、登录、投递列表、详情、本人隔离和匿名 401 正常，测试数据库可用。

## 覆盖验收标准

- 所有九类共享端点匿名 401、统一错误结构；精确 ID 校验、自身/不存在/停用隐藏。
- 新注册及既有 User fixture 的头像有效、稳定、公共结构不暴露邮箱，me/搜索/申请头像一致。
- 推荐默认 10 与可配置 1/3/50、空结果、去重、排除本人/停用/双向 pending/connected；非法环境配置拒绝检查。
- 申请、双方历史与第三方隔离、伪造 sender/owner/status 无授权、重复和反向申请冲突、并发仅一个有效 pending。
- 只有接收方可以显式接受或拒绝，pending/rejected 不授权；拒绝后重新申请不覆盖历史；历史保留最近 100 项且倒序。
- 同意后双向共享，只读字段与原创建输出一致去除 notes/user；六阶段时间/时长和投递链接保留；第三方无共享关系/阅读/解除权限。
- 共享后旧详情 GET/PATCH/DELETE 和旧列表 user 参数仍保持本人隔离；共享入口非 GET 不能修改记录。
- 任何一方单方 DELETE 即时双向撤销、下一次读 404、双方关系/名单清空、历史 revoked、可重新申请且仍须同意。
- 停用已共享用户隐藏并拒绝读；默认 20、10/20/50/100、公司和岗位搜索、稳定倒序、超页空、非法分页 400。

## 未覆盖风险与复测范围

- 随机推荐不要求每次刷新必然变化；随机头像不做小样本分布断言，避免概率性失败。
- 旧用户通过公开 User fixture 模拟，不在测试中读取迁移或内部 profile；真实旧库迁移证据由实现/验收提供。
- 独立复测需全部 41 个专项、APP-003～008 相关投递及 AUTH-001～004/SEC-001 认证权限回归。前端由另一个测试 Agent 独立处理。

## Agent 交接

- 任务编号：SHARE-001。
- 当前状态：RED_CONFIRMED（已向项目管理同步，由项目管理更新任务单）。
- 接收角色：功能实现 Agent share_implementation。
- 允许修改：任务单声明的生产范围与实现说明；测试保持只读。
- 输入文档：`docs/requirements/SHARE-001.md`、`docs/tasks/SHARE-001.md`、本报告及专项测试。
- 完成条件：实现全部公开行为，提供迁移/运行时配置和实现说明，进入 READY_FOR_TEST 后通知原测试 Agent 独立复测。
