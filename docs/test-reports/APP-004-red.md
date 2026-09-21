# APP-004 RED 报告

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 工作目录：`G:/job`
- 环境：PostgreSQL 17.11，`127.0.0.1:5432`；`DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`
- 测试文件：`G:/job/backend/tests/test_app_004.py`

## 命令与结果

```text
uv run --no-sync pytest tests/test_app_004.py --tb=no -q
```

最终测试侧断言修正后，结果为：

```text
10 failed, 3 passed in 27.72s
```

此前一次收集错误来自测试文件换行伪字符，已在测试目录内修正；不计入 RED 结果。页码越界按任务契约允许的固定 `404` 行为处理，不以该行为判定失败。

## 覆盖的公开契约

- 默认 `page=1`、`page_size=20`；
- `page_size` 为 `10/20/50/100` 时生效；
- 超过 100 或非法 page_size 返回 `400 VALIDATION_ERROR`；
- 页码越界固定行为（允许 `200` 空结果或 `404`）；
- `next/previous` 保留 `page_size` 等 query 参数；
- 超过一页时只统计并返回当前用户记录，不计入其他用户。

## 失败证据

聚焦复核确认当前公开行为缺失或不符合 APP-004：

```text
?page_size=10：响应 page_size 实际为 20，未按请求生效
?page_size=101：实际 200，未返回预期 400 VALIDATION_ERROR
```

完整运行中 10 项稳定属于分页参数校验/生效及 next/previous query 保留行为失败；默认分页、允许的 page_size=20 以及越界 404 行为通过。失败不是依赖、数据库或语法错误。

## 结论

`RED_CONFIRMED`：APP-004 分页参数行为及链接 query 保留缺口已形成真实 RED 证据。未修改生产实现目录。

黑盒声明：未读取或分析生产实现代码。
