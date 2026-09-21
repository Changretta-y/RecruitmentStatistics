# APP-007 RED 报告

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 工作目录：`G:/job`
- 环境：PostgreSQL 17.11，`127.0.0.1:5432`；`DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`
- 测试文件：`G:/job/backend/tests/test_app_007.py`

## 命令与结果

```text
uv run --no-sync pytest tests/test_app_007.py --tb=no -q
```

结果：

```text
3 failed, 1 passed in 6.60s
```

聚焦复核结果：`2 failed, 1 passed`，测试正常收集，认证、创建数据和数据库访问夹具可运行。

## 覆盖的公开契约

- 本人 DELETE 返回 `204 No Content`，记录硬删除；
- 删除后列表和详情不可见；
- 跨用户、不存在 ID、重复删除统一 `404 NOT_FOUND` 且目标不变；
- 未认证 DELETE 返回 `401` 且记录保持可见。

## 稳定失败证据

聚焦复核显示：

```text
本人 DELETE：实际 405 Method Not Allowed，预期 204
跨用户 DELETE：实际 405 Method Not Allowed，预期 404
未认证 DELETE：通过，返回预期 401
```

跨用户和不存在 ID 的 DELETE 均被公开路由以 `405` 拒绝，尚未进入契约要求的统一 404 行为。失败来自 DELETE 业务行为缺失，不是语法、夹具、依赖或数据库环境错误。

## 结论

`RED_CONFIRMED`：APP-007 本人删除、硬删除及资源存在性安全边界已形成真实 RED 证据。未修改生产实现目录。

黑盒声明：未读取或分析生产实现代码。
