# APP-006 RED 报告

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 工作目录：`G:/job`
- 环境：PostgreSQL 17.11，`127.0.0.1:5432`；`DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`
- 测试文件：`G:/job/backend/tests/test_app_006.py`

## 命令与结果

```text
uv run --no-sync pytest tests/test_app_006.py --tb=no -q
```

结果：

```text
14 failed, 1 passed in 18.74s
```

测试正常收集并执行，认证、创建数据和数据库访问夹具可运行。聚焦复核命令：

```text
uv run --no-sync pytest tests/test_app_006.py::test_patch_one_field_preserves_other_mutable_fields_and_returns_full_record tests/test_app_006.py::test_cross_user_patch_returns_404_and_leaves_owner_record_unchanged tests/test_app_006.py::test_unauthenticated_patch_returns_401_and_leaves_record_unchanged --tb=short -q
```

结果：`2 failed, 1 passed`。

## 覆盖的公开契约

- PATCH 单字段部分更新且其他字段保持不变；
- 六个阶段时间分别设置、修改、JSON `null` 清空及 `current_stage` 派生；
- 带时区 ISO 时间更新并按 UTC 语义返回；
- 非法时间、空字符串、非法状态返回字段级 `400 VALIDATION_ERROR` 且不变更；
- id/user/current_stage/created_at/updated_at 只读字段不可覆盖；
- 跨用户 PATCH 返回 `404` 且原记录不变；
- 未认证 PATCH 返回 `401`。

## 稳定失败证据

聚焦复核显示：

```text
本人单字段 PATCH：实际 405 Method Not Allowed，预期 200
跨用户 PATCH：实际 405 Method Not Allowed，预期 404
未认证 PATCH：通过，返回预期 401
```

当前 `/api/v1/applications/{id}/` 尚未提供 PATCH 公开行为，导致合法更新、阶段操作、校验、只读字段和跨用户边界测试失败。失败来自缺失业务行为，不是语法、夹具、依赖或数据库环境错误。

## 结论

`RED_CONFIRMED`：APP-006 PATCH 修改与阶段时间清空行为已形成真实 RED 证据。未修改生产实现目录。

黑盒声明：未读取或分析生产实现代码。
