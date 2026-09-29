# APP-009 TEST_PASSED

- 测试角色：company_tests，原独立测试 Agent；全程仅承担测试角色。
- 状态：`TEST_PASSED`（任务范围）。
- 复测生产提交：`ad3a305`；测试先行 `df4d8eb`；共享隐私契约修正测试 `6195565`；任务交接 `c54b9ce`。
- 环境：Windows；Python 3.11.13；uv 0.7.21；PostgreSQL 17.11 独立集群 `127.0.0.1:55439`、合成用户/数据库 app009_test。依赖 frozen 同步成功；测试库实际名称为 app009_test_test。
- 所有数据库测试串行运行，无并发迁移或测试库占用；未读取真实环境凭据或连接生产。

## 独立命令与正式统计

仓库根目录 PowerShell：

```powershell
& backend/tests/run-isolated-postgres.ps1
& backend/tests/run-isolated-postgres.ps1 -PytestArguments @('tests','--tb=no','-q')
& backend/tests/run-isolated-postgres.ps1 -PytestArguments @('tests/docs/test_doc_001.py::test_public_docs_do_not_contain_real_credentials_or_production_addresses','--tb=line','-q')
```

- APP-009 专项：**25 passed in 34.09s**，exit 0。
- 完整 backend/tests：**310 passed / 1 failed / 0 errors in 417.04s**，exit 1。
- 唯一失败的 DOC-001 文档正则定向复跑：**1 failed in 0.10s**，exit 1。
- 不宣称全量套件全绿；本任务与所有相关认证、CRUD、查询分页、时长、日历、邮件、共享、安全回归用例均在 310 项通过中。

## 业务结果与 RED 对照

- 原 nested POST 返回 400，现公司多岗位创建返回 201；详情/列表/PATCH 保留独立岗位状态、投递时间、备注，省略岗位不删除。
- 同一用户标准化同名公司追加到同一公司 ID，重复岗位允许，不影响其他用户公司。
- AI 面、测评、笔试唯一且按类型更新；重复类型顺序更新，清空时间清空时长；最近阶段派生正确。
- 岗位可以包含同名多面试，各自稳定 ID；子资源和嵌套更新仅影响目标，省略项保留；缺省时长为 60。
- 原新增子资源未认证返回 404，现完整 CRUD/面试/岗位子资源未认证返回 401；跨用户或错误父资源返回 404。
- 非法嵌套阶段/日期/时长拒绝，父公司及岗位更新不部分保存；公司撞名和他公司岗位 ID 不更改任一公司。
- 删除指定岗位保留同级与公司，最后岗位不能删除；公司删除后详情/子资源不可访问。
- 公司/岗位搜索、状态筛选、排序和公司分页正确，返回完整岗位集合。
- 公开历史迁移基线 0003 播种两个混合大小写/首尾空白的旧公司记录，再迁移最新并通过认证 API 观察：原 count=2，现 count=1；全部岗位、URL、备注、面试日期与时长保留，AI 时间冲突选最早及其对应 37 分钟。
- 新共享隐私案例通过：含两岗位私密备注的 nested 公司不会自动公开 positions/shared_stages 或备注；共享输出保持明确旧 21 字段白名单及字段值一致，双向授权/只读/第三方隔离/撤销立即拒绝仍通过。

## 唯一既存文档失败证据

- 失败：`tests/docs/test_doc_001.py::test_public_docs_do_not_contain_real_credentials_or_production_addresses`。
- 命中规则为 password/secret/token 等值的通用文本正则，当前命中仅 `README.md:114` 与 `docs/requirements/CAL-001.md:56`，未复制匹配值。
- 任务前既存证据：`git diff df4d8eb^ HEAD -- README.md docs/requirements/CAL-001.md backend/tests/docs/test_doc_001.py` 零差异。
- `docs/test-reports/SHARE-001-passed.md` 已记录同两个文档的数据库密码占位提示与 token URL 占位示例误报，原项目管理已裁定可按任务范围通过。本次文档与检测断言均未改动，定向重跑仍命中相同既存内容。
- 未跳过或放宽该断言；保留完整回归实际 exit 1，提交项目管理按任务范围验收。

## 未覆盖风险与交接

- 迁移历史冲突统计属实现/验收交付，由实现说明报告；此次合成数据只覆盖一个共享类型冲突与两个岗位。
- 新增 assessment 独立查询排序、非空数据逆迁移拒绝与大规模迁移/并发压力不在本次 25 项专项断言内，可由项目管理公开验收补充。完整原查询和全部相邻公开接口回归已通过。
- 不将实现自检计入独立复测结果。通过报告交项目管理验收，只有项目管理设置 DONE；WEB-APP-006 测试阶段须在后端验收完成后启动。

## 黑盒声明

未读取、搜索、枚举或分析 backend/apps、生产 backend/config 或 frontend/src。只读取公开契约、任务交接、实现说明和测试。迁移通过公开 MigrationExecutor 历史状态播种，业务结果通过认证 HTTP API 观察；本轮只新增本测试报告，不修改生产代码或原有效断言。
