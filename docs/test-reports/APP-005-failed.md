# APP-005 TEST_FAILED 报告

- 测试角色：测试 Agent
- 状态：`TEST_FAILED`
- 工作目录：`G:/job`
- 环境：PostgreSQL 17.11，`127.0.0.1:5432`；`DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`
- 生产实现：未修改

## 专项命令与结果

```text
uv run --no-sync pytest tests/test_app_005.py --tb=no -q
```

结果：

```text
4 failed, 17 passed in 42.98s
```

## 相关回归命令与结果

```text
uv run --no-sync pytest tests/test_app_005.py tests/test_app_004.py tests/test_app_003.py tests/test_app_002.py tests/test_app_001.py tests/test_auth_004.py tests/test_auth_003.py tests/test_auth_002.py tests/test_auth_001.py tests/test_db_001.py tests/test_health.py tests/test_urls.py --tb=no -q
```

结果：

```text
4 failed, 95 passed in 123.16s (0:02:03)
```

## 失败证据与契约核查

4 个失败均来自当前测试断言与公开契约/测试数据不一致，不是环境或生产行为证据：

1. `search=Needle`：公开契约要求匹配公司名或岗位名。当前夹具中 `alpha` 的公司名匹配，`beta` 的岗位名也匹配；测试却只断言 `alpha`，应改为同时期待 `alpha` 和 `beta`，并继续排除另一用户记录。
2. `application_status=applied`：当前夹具中 `alpha`、`zeta`、`theta` 三条均为 `applied`；公开契约是按状态过滤全部匹配记录，测试却断言 `count == 1`。
3. `application_status=in_progress`：当前夹具中 `beta`、`eta` 两条均为 `in_progress`；测试却断言 `count == 1`。
4. `application_time_before=2026-03-03T00:00:00+08:00`：公开实现说明记录 `before` 使用小于等于语义；`gamma` 的投递时间为 2026-03-10，应被排除，测试却把 `gamma` 纳入期望结果。正确期望应为 `alpha`、`beta`。

其余 17 项专项测试通过，覆盖阶段筛选、时间 after、完整正/倒序白名单、默认排序、空时间置后、组合筛选分页及非法筛选/排序 `400 VALIDATION_ERROR`。相关回归其余 95 项通过。

## 是否需要修正测试

需要。应修正上述 4 个测试断言/期望集合后再复测；本轮不修改测试以制造通过，也不将这 4 项归因于生产实现失败。修正后需重新运行 APP-005 专项及完整相关回归。

## 结论

`TEST_FAILED`：当前 APP-005 测试文件不能作为实现失败证据；失败集中为已确认的测试断言与公开契约矛盾，回流测试 Agent 修正测试后复测。

黑盒声明：未读取或分析生产实现代码。


## 回流修正依据记录

根据公开任务契约和现有夹具，下一轮测试仅修正断言期望，不改变测试覆盖范围：

- search 是公司名或岗位名的模糊匹配，因此 Needle 应返回当前用户的 alpha（公司命中）和 beta（岗位命中），并排除另一用户记录；
- 状态筛选返回当前用户全部匹配记录：applied 为 alpha/zeta/theta，in_progress 为 beta/eta，其他状态各为对应单条记录；
- application_time_before 使用包含边界的时间上限；2026-03-03 之前不应包含 gamma 的 2026-03-10 投递时间，期望仅为 alpha/beta。
