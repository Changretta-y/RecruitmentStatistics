# APP-002 RED 报告

状态：`RED_CONFIRMED`

## 测试范围

新增黑盒测试：`G:/job/backend/tests/test_app_002.py`

覆盖公开契约：

- 带 Bearer Access Token 创建申请，预期 `201`、完整 snake_case 响应、当前用户归属及数据库持久化；
- 创建时 status/notes/申请时间与六阶段时间的默认值和 `null` 行为；
- 缺失或空白公司/职位、非法 status、非法 ISO 时间返回结构化 `400 VALIDATION_ERROR`，且不落库；
- 请求体伪造 user 不得改变 token 对应用户归属；
- 未认证创建返回 `401` 且不落库；
- 响应不得包含密码或 token 等敏感字段。

## 环境与命令

- 工作目录：`G:/job`
- PostgreSQL：17.11，`127.0.0.1:5432`
- `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`
- 测试命令：

  `uv run --no-sync pytest tests/test_app_002.py --tb=no -q`

## 实际结果

同一测试命令连续执行两次，结果均为：

```text
10 failed in 11.10s
10 failed in 11.13s
```

失败原因稳定且属于缺失业务行为，不是语法、夹具、依赖或数据库环境错误。聚焦复核显示：

```text
authenticated create: assert 404 == 201
unauthenticated create: assert 404 == 401
Not Found: /api/v1/applications/
```

当前公开创建路由 `/api/v1/applications/` 返回 `404 Not Found`，因此创建成功、校验错误、归属和未认证边界均无法满足 APP-002 契约。测试正常收集并执行，认证注册/登录及数据库访问夹具可运行。

## 结论

`RED_CONFIRMED`：已确认 APP-002 当前实现缺少公开申请创建端点/行为。未修改生产目录。
