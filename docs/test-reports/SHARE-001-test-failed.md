# SHARE-001 TEST_FAILED

> 历史诊断记录：项目管理随后核对为任务前已存在的占位文本误报，`git show 4ee597a` 同规则同位置命中且文件未改；任务范围结论及风险见 `SHARE-001-passed.md`。本记录保留原始失败证据，不再表示当前任务状态。

- 测试角色：share_tests（原独立测试 Agent）。
- 输入实现：`4238383`；实现说明 `docs/implementation-notes/SHARE-001.md`。
- 环境：Windows PowerShell，Python 3.11.13，uv 0.7.21，本地 PostgreSQL 127.0.0.1:5432；`uv sync --frozen --group test` 完成，后续 `uv run --no-sync`；测试专属数据库与至少32字符SECRET；全部数据库测试串行。
- 黑盒声明：未读取、搜索、枚举或分析生产实现；仅任务/说明、测试、公开 HTTP、公开文档检查和schema管理命令。

## 独立专项

工作目录 `G:/job/backend`：

```text
uv run --no-sync pytest tests/test_share_001.py --reuse-db --tb=no -q
```

结果：**41 passed / 0 failed / 0 errors**，85.61秒。双向显式授权、任一方立即双向解除、并发唯一、头像、推荐配置、只读字段/备注隐私、旧CRUD隔离、分页/搜索和历史100项均通过。

## 必要联合回归

```text
uv run --no-sync pytest tests/test_app_003.py tests/test_app_004.py tests/test_app_005.py tests/test_app_006.py tests/test_app_007.py tests/test_app_008.py tests/test_auth_001.py tests/test_auth_002.py tests/test_auth_003.py tests/test_auth_004.py tests/test_sec_001.py tests/docs/test_doc_001.py tests/test_cal_002.py --reuse-db --tb=no -q
```

结果：**186 passed / 1 failed / 0 errors**，225.12秒。

唯一失败：`tests/docs/test_doc_001.py::test_public_docs_do_not_contain_real_credentials_or_production_addresses`。

- 公开输入：当前 README 与公共 docs/需求文档内容。
- 期望：未匹配 credentials/production-address 禁止规则。
- 实际：凭证规则2 `(?:password|passwd|secret|token)\s*[:=]\s*['"]?[^\s'"]{8,}` 匹配 `README.md:95`、`docs/requirements/CAL-001.md:56`。未打印匹配原值，不将潜在凭据写入报告；另两条URL规则无匹配。
- 稳定复现：单独运行该测试（`--reuse-db --tb=line -q`）仍 **1 failed**，0.08秒。
- 当前归因：与共享 HTTP 行为无关的既有公共文档回归。已经交项目管理确认具体匹配内容是否占位/变量误报；测试 Agent 未改既有断言，未自行豁免失败。

## OpenAPI 公共检查

通过公共 `uv run --no-sync python manage.py spectacular --format openapi-json --file <临时文件> --validate` 独立生成解析：退出 **0**；共享8路径9操作完整（me、推荐、搜索、申请GET/POST、回应、连接GET、解除DELETE、记录GET）。DOC001 schema契约用例通过，日历schema兼容回归未失败。

完整schema仍报告 **Warnings: 0，Errors: 16（3 unique）**；实现说明说明为既有通知三接口缺serializer，本次共享接口均生成。命令退出0不等同全项目schema不存在已有不足。

## 交接

- 当前状态：TEST_FAILED；已向项目管理同步，不设置TEST_PASSED。
- 回流责任：项目管理先确认这两个公共文档匹配内容与修复归属；若确认需求/文档不符合既有检查，分派有写权限的角色修正；若确认测试与已批准公开契约不一致，给测试 Agent 明确裁决再修测试。
- 再复测：复现失败及DOC001全套；若修复影响生产，再跑受影响功能测试；现有专项和186个回归通过结果保留。
- 未覆盖风险：生产部署未执行；旧库头像迁移证据在实现说明的隔离数据库中，测试未读取内部迁移；概率行为不要求推荐每次必然不同。
