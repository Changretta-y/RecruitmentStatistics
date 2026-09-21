# APP-006 独立复测报告

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 工作目录：`G:/job`
- PostgreSQL：17.11，`127.0.0.1:5432`
- `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`
- 未修改生产实现目录。

## 专项测试

```text
uv run --no-sync pytest tests/test_app_006.py --tb=no -q
```

结果：

```text
15 passed in 18.25s
```

验证通过：

- PATCH 单字段部分更新并保持其他字段；
- 六个阶段分别 set、modify、JSON `null` 清空及 `current_stage` 派生；
- 带时区 ISO 时间及 UTC 语义；
- 非法时间、空字符串、非法状态返回字段错误且不落库；
- 只读字段无法篡改；
- 跨用户 PATCH 返回 `404` 且记录不变；
- 未认证 PATCH 返回 `401`。

## 相关回归

```text
uv run --no-sync pytest tests/test_app_006.py tests/test_app_005.py tests/test_app_004.py tests/test_app_003.py tests/test_app_002.py tests/test_app_001.py tests/test_auth_004.py tests/test_auth_003.py tests/test_auth_002.py tests/test_auth_001.py tests/test_db_001.py tests/test_health.py tests/test_urls.py --tb=no -q
```

结果：

```text
114 passed in 141.83s (0:02:21)
```

## 结论

`TEST_PASSED`：APP-006 专项及 APP-005～APP-001、Auth、DB、health、urls 相关回归全部通过。

黑盒声明：未读取或分析生产实现代码。
