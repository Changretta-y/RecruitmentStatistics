# APP-004 独立复测报告

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 工作目录：`G:/job`
- PostgreSQL：17.11，`127.0.0.1:5432`
- `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`

## 目标测试

命令：

```text
uv run --no-sync pytest tests/test_app_004.py --tb=no -q
```

结果：

```text
13 passed in 27.65s
```

验证通过：

- 默认 `page=1`、`page_size=20`；
- `page_size=10/20/50/100` 正常生效；
- 非法值及超过 100 返回固定 `400 VALIDATION_ERROR`；
- 超页行为固定且结果为空/符合契约；
- `next`、`previous` 保留分页 query 参数；
- 多页数据只计入当前用户，不跨越用户隔离边界。

## 关联回归

命令：

```text
uv run --no-sync pytest tests/test_app_004.py tests/test_app_003.py tests/test_app_002.py tests/test_app_001.py tests/test_auth_004.py tests/test_auth_003.py tests/test_auth_002.py tests/test_auth_001.py tests/test_db_001.py tests/test_health.py tests/test_urls.py --tb=no -q
```

结果：

```text
78 passed in 85.81s (0:01:25)
```

## 结论

`TEST_PASSED`：APP-004 目标测试及 APP-003、APP-002、APP-001、Auth、DB、health、urls 关联回归全部通过。未修改生产实现目录。

黑盒声明：未读取或分析生产实现代码。
