# APP-003 RED 报告

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 工作目录：`G:/job`
- 环境：PostgreSQL 17.11，`127.0.0.1:5432`；`DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖命令：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`
- 测试文件：`G:/job/backend/tests/test_app_003.py`

## 命令与结果

执行命令：

```text
uv run --no-sync pytest tests/test_app_003.py --tb=no -q
```

同一命令连续执行两次，结果分别为：

```text
7 failed in 10.57s
7 failed in 10.65s
```

测试正常收集并执行，失败稳定复现。

## 覆盖的公开契约

- Bearer Access Token 认证的本人列表和本人详情；
- 默认分页容器 `count/page/page_size/total_pages/next/previous/results`；
- 本人列表与详情完整响应、空列表；
- 两用户列表和详情隔离；
- 猜测他人 ID 与不存在 ID 均返回 `404 NOT_FOUND`；
- `user` query 参数不得绕过服务端归属过滤；
- 未认证列表和详情均返回 `401`。

## 稳定失败证据

聚焦复核显示：

```text
认证列表：实际 405 Method Not Allowed，预期 200
认证本人详情：实际 404 Not Found，预期 200
未认证详情：实际 404 Not Found，预期 401
```

公开请求路径为 `/api/v1/applications/` 及 `/api/v1/applications/{id}/`。失败来自列表/详情公开行为尚未满足 APP-003 契约，不是语法、夹具、依赖或数据库环境错误。

## 结论

`RED_CONFIRMED`：APP-003 列表/详情及认证隔离行为已形成稳定 RED 证据。未修改生产实现目录。

黑盒声明：未读取或分析生产实现代码。
