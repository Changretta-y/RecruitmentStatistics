# APP-005 独立复测报告

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 工作目录：`G:/job`
- 环境：PostgreSQL 17.11，`127.0.0.1:5432`；`DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`
- 修改范围：仅修正 `G:/job/backend/tests/test_app_005.py` 中已确认与公开契约矛盾的 3 类期望；未修改生产实现。

## 修正依据

- `search` 是公司名或岗位名的模糊匹配，`Needle` 同时命中当前用户的公司 `alpha` 和岗位 `beta`，并排除另一用户记录；
- 状态筛选返回全部匹配记录：`applied` 为 `alpha/zeta/theta`，`in_progress` 为 `beta/eta`；
- `application_time_before=2026-03-03` 按包含上限处理，排除 2026-03-10 的 `gamma`，期望为 `alpha/beta`。

修正依据已先记录于 [APP-005-failed.md](G:/job/docs/test-reports/APP-005-failed.md) 的“回流修正依据记录”章节。

## 专项命令与结果

```text
uv run --no-sync pytest tests/test_app_005.py --tb=no -q
```

结果：

```text
21 passed in 43.45s
```

覆盖搜索、当前用户隔离、五种状态、六阶段已填筛选、时间 after/before、全部排序白名单正倒序、默认排序、非法参数、组合筛选分页及空时间排序约定。

## 完整 APP 回归

```text
uv run --no-sync pytest tests/test_app_005.py tests/test_app_004.py tests/test_app_003.py tests/test_app_002.py tests/test_app_001.py --tb=no -q
```

结果：

```text
61 passed in 91.27s (0:01:31)
```

## 结论

`TEST_PASSED`：修正后的 APP-005 专项及 APP-001 至 APP-005 完整 APP 回归全部通过。未修改生产实现目录。

黑盒声明：未读取或分析生产实现代码。
