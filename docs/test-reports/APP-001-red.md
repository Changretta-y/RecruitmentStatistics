# APP-001 RED

- 测试角色：测试 Agent
- 状态：RED_CONFIRMED
- 工作区：G:\job
- 环境：Windows；PostgreSQL 17.11（127.0.0.1:5432）；uv 0.7.21；Python 3.11.13
- DATABASE_URL：postgresql://postgres:postgres@127.0.0.1:5432/postgres
- 依赖同步：uv sync --frozen --group test，成功

## 测试命令与结果

新增测试文件：backend/tests/test_app_001.py

命令：

uv run --no-sync pytest tests/test_app_001.py --tb=no -q

连续两次结果：

- 10 failed in 5.37s
- 10 failed in 5.50s

失败覆盖：

- JobApplication 模型注册和 job_applications 迁移表。
- 默认状态、备注、六个空阶段时间。
- 公司名/岗位名/状态字段校验。
- 带时区时间读写和 updated_at 更新。
- current_stage 六阶段优先级与终态状态优先。
- 用户级联删除。
- 用户相关索引。

## 实际失败原因

测试体内公开模型注册断言失败：Django app registry 未注册 JobApplication 模型。该失败发生在正常 pytest 测试执行中，不是语法错误、测试收集错误、夹具导入错误或数据库连接错误；缺失模型注册直接阻断了对应迁移、字段、派生阶段、级联和索引契约。

## 期望行为

- JobApplication 注册并由迁移创建 job_applications 表。
- 六个阶段时间可空，默认状态 applied、备注为空字符串。
- 字段校验、时区时间、updated_at 和 current_stage 规则符合 APP-001。
- 用户删除级联删除记录，且声明用户+更新时间、用户+状态、用户+公司名索引。

## 是否稳定复现

是。同一测试集连续两次均为 10 failed；uv 同步成功，pytest 正常收集并执行。

## 覆盖的验收标准

覆盖 APP-001 任务单全部验收标准：迁移/模型持久化、默认值、字段校验、时区与更新时间、六阶段优先级/终态、级联删除和索引。

## 未覆盖风险

模型注册和迁移完成后，需要由测试 Agent 使用同一测试集继续验证具体字段和运行时行为。

- 黑盒声明：仅依据任务契约、公开 Django app registry、模型元数据和 PostgreSQL pytest 数据库行为设计测试；未读取或分析 backend/apps、backend/config 或 frontend/src 生产实现代码。