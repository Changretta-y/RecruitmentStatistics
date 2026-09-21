# APP-005 RED 报告

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 工作目录：`G:/job`
- 环境：PostgreSQL 17.11，`127.0.0.1:5432`；`DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 依赖同步：`uv sync --frozen --group test` —— 成功，`Audited 17 packages`
- 测试文件：`G:/job/backend/tests/test_app_005.py`

## 命令与结果

```text
uv run --no-sync pytest tests/test_app_005.py --tb=no -q
```

结果：

```text
20 failed, 1 passed in 43.31s
```

测试正常收集并执行；创建数据、认证和数据库访问夹具均可运行。聚焦复核命令也正常执行并复现筛选/排序行为失败。

## 覆盖的公开契约

- `search` 对公司名和岗位名模糊匹配，并保持当前用户隔离；
- 五种 `application_status` 筛选；
- 六个阶段的已填写筛选，并排除未填写记录；
- `application_time_after` / `application_time_before` ISO 时间范围；
- `created_at`、`updated_at`、`application_time` 与六个阶段字段的正/倒序白名单排序；
- 默认 `-updated_at,-id` 排序；
- 组合筛选、排序与分页；
- 非法状态、阶段、时间和 ordering 统一返回 `400 VALIDATION_ERROR`；
- 空时间排序约定：正序和倒序均将 `null` 置于非空值之后。

## 失败证据

聚焦复核：

```text
search=Needle：实际返回当前用户全部 8 条，预期仅匹配记录
application_status=applied：实际 count=8，预期 count=1
ordering=not_allowed：实际 200，预期 400 VALIDATION_ERROR
```

完整运行中筛选、阶段、时间范围、白名单排序、组合查询和非法参数测试均未满足契约；默认排序稳定性测试通过。失败来自公开筛选/排序行为尚未实现，不是语法、夹具、依赖或数据库环境错误。

## 结论

`RED_CONFIRMED`：APP-005 搜索、筛选、排序和非法参数校验已形成真实 RED 证据。未修改生产实现目录。

黑盒声明：未读取或分析生产实现代码。
