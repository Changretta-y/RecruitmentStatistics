# APP-009 RED_CONFIRMED

- 测试角色：测试 Agent；仅承担测试角色。
- 状态：`RED_CONFIRMED`。
- 环境：Windows；Python 3.11.13；uv 0.7.21；PostgreSQL 17.11。`uv sync --frozen --group test --python 3.11.13` 成功。
- 原阻塞：默认 localhost:5432 缺少认证密码及明确数据库名，pytest 无法创建测试数据库，业务断言未执行；这不是业务 RED。
- 处理：独立临时 PostgreSQL 集群，目录 `$env:TEMP/job-app009-postgres-55439/data`，只监听 `127.0.0.1:55439`，专用合成用户/数据库 `app009_test`，本机临时集群 trust。未读取真实 `.env`、未猜现有数据库密码、未连接生产数据。
- 入口：`backend/tests/run-isolated-postgres.ps1` 自动初始化/复用集群、建库、同步冻结测试依赖，并在测试进程注入 `DATABASE_URL=postgresql://app009_test@127.0.0.1:55439/app009_test` 与合成 `DJANGO_SECRET_KEY`，退出恢复原环境。PostgreSQL 启动使用隐藏进程；集群保持运行供实现与独立复测复用。

## 命令与实际结果

仓库根目录 PowerShell：

```powershell
& backend/tests/run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_008.py::test_unauthenticated_create_with_durations_returns_401','--tb=no','-q')
& backend/tests/run-isolated-postgres.ps1
```

- APP-008 认证探针：`1 passed in 23.20s`，数据库与旧认证 API 可用。
- APP-009 第一次完整运行：`22 failed, 3 passed in 29.31s`，25 项，零环境/夹具 ERROR。
- 强化迁移大小写、URL、备注、时间、时长断言后的第二次完整运行：`22 failed, 3 passed in 30.37s`，失败稳定。
- 精简诊断复跑三个关键测试：`3 failed in 4.51s`；只输出测试断言行，不沿生产调用栈调查。
- 冻结实施前公开迁移基线 `applications/0003_jobapplication_stage_durations` 后迁移单测：`1 failed in 3.59s`，仍为公开列表公司数 `2 != 1`。

## 公开输入、期望与实际

- POST 公司名、两个岗位、三类共享流程：期望 201 及独立岗位/唯一共享类型；实际 400。缺少新嵌套创建行为导致后续 CRUD/边界测试在这个公开前置条件失败。
- 未认证调用面试子资源：期望 401；实际 404，公开子资源路由尚未提供。
- 公开历史迁移状态播种同一用户的 `  Migration Tech  ` / `migration TECH` 两个岗位，分别安排 AI 面与岗位面试及其时长，迁移后登录读取列表：期望一个公司/两个岗位；实际公司 count 为 2。
- 空岗位/公司名/岗位名校验三个用例已通过；尚未覆盖新增聚合行为。

## 覆盖范围

- 多岗位创建/详情/列表、岗位独立状态/时间/备注、PATCH 追加与省略保留。
- 标准化同名 POST 归并、重复同名岗位允许、跨用户同名公司隔离。
- AI 面/测评/笔试唯一性、同请求重复类型顺序更新、清空日期联动清空时长。
- 岗位同名多面试、稳定 ID、子资源增改删、嵌套更新与省略保留、默认时长与最近阶段推导。
- CRUD/子资源未认证行为、所有者/父资源隔离、他公司岗位 ID、撞名更新原子性。
- 非法阶段/日期、无时间时长、越界/布尔时长的嵌套 PATCH 原子性。
- 删除指定岗位保留同级、拒绝删最后岗位、公司删除后公开子资源不可写。
- 公司/岗位搜索、状态筛选、排序、公司分页并返回完整岗位集合。
- PostgreSQL 历史迁移：空白/大小写合并，保留所有岗位/备注/URL；最早 AI 时间及对应时长；岗位面试时间/时长；未安排阶段不生成岗位面试。

## 风险与交接

- 完成实现后须运行本集及原认证/权限/APP-008、日历/邮件/共享兼容回归；RED 阶段仅完成 APP-008 认证环境探针，不声明兼容回归通过。
- 历史冲突数量由实现说明记录并由项目管理验收检查。
- 并发岗位追加、大规模迁移性能未覆盖，当前契约未要求新增性能目标。
- 接收角色：实现 Agent；建议自测使用上述入口，完成生产实现与迁移后交 READY_FOR_TEST，由测试角色独立复测。测试目录只读。

## 黑盒声明

未读取、搜索、枚举或分析 `backend/apps/`、生产 `backend/config/`、`frontend/src/`。仅读取需求、任务单、测试与公开历史迁移状态；迁移后只观察认证 API。未修改生产代码、运行时依赖或其他角色交付物。
