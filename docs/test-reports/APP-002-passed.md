# APP-002 独立复测报告

状态：`TEST_PASSED`

## 环境

- 工作目录：`G:/job`
- PostgreSQL：17.11，`127.0.0.1:5432`
- `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 测试依赖：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`

## 验证范围

黑盒验证 APP-002 公开契约：

- 已认证创建申请返回 `201` 和完整响应；
- 默认值、`null` 阶段时间、时区转换及字段校验；
- 当前 Access Token 用户归属，伪造 `user` 不得转移归属；
- 未认证请求返回 `401` 且不创建记录；
- 响应不泄露密码、哈希或 token 等敏感字段。

## 命令与结果

目标测试：

```text
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres \
uv run --no-sync pytest tests/test_app_002.py --tb=no -q
```

结果：

```text
10 passed in 11.39s
```

关联回归：

```text
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres \
uv run --no-sync pytest tests/test_app_002.py tests/test_app_001.py \
tests/test_auth_004.py tests/test_auth_003.py tests/test_auth_002.py \
tests/test_auth_001.py tests/test_db_001.py tests/test_health.py \
tests/test_urls.py --tb=no -q
```

结果：

```text
58 passed in 48.30s
```

## 结论

`TEST_PASSED`：APP-002 独立复测及相关回归全部通过。未修改生产实现目录。
