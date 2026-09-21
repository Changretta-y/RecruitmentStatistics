# DOC-001 RED 测试报告

## 状态

RED_CONFIRMED

## 测试角色与黑盒边界

- 测试角色：测试 Agent
- 新增测试：`backend/tests/docs/test_doc_001.py`
- 仅观察公开 schema endpoint、`manage.py` 公开生成命令和公开文档文本
- 未读取或分析生产实现源码，未修改生产或文档实现

## 环境与命令

- 工作目录：`G:\job\backend`
- PostgreSQL：`127.0.0.1:5432`
- `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- uv 依赖同步：`uv sync --frozen --group test` 成功
- 测试环境使用仅限测试进程的长 secret
- 执行命令：

  ```text
  uv run --no-sync pytest tests/docs/test_doc_001.py --tb=no -q
  ```

## 结果

```text
3 failed, 1 passed in 2.50s
Exit code: 1
```

## 真实缺口证据

### Schema 入口/生成缺失

测试探测以下公开 schema endpoint，均未返回可用 schema：

```text
/api/schema/
/api/v1/schema/
/api/schema.json
/api/v1/schema.json
```

随后执行公开 schema 生成命令：

```text
uv run --no-sync python manage.py spectacular --file <temporary-openapi.json>
```

实际结果：

```text
Unknown command: 'spectacular'
Type 'manage.py help' for usage.
Exit code: 1
```

因此无法验证注册、登录、refresh、logout、me、投递 CRUD、查询分页、错误结构或 Bearer security scheme；失败原因是公开 schema 入口和生成命令缺失，不是测试环境或数据库错误。

### 文档命令缺口

公开开发/部署文档检查失败，缺少以下可执行说明：

- `uv sync --frozen`；
- `uv run` 后端命令入口；
- 数据库 `migrate`；
- `nvm use`；
- `npm ci`；
- `npm run test` 前端测试入口。

E2E 相关词汇存在，但不能替代完整的前后端启动、迁移和测试命令说明。

## 通过项

- 公开文档敏感凭据、密码、Token 和生产地址扫描通过；
- 测试依赖同步和 pytest 运行正常。

## 覆盖范围

新增测试覆盖 schema endpoint/生成命令、认证与投递 CRUD 路径、查询/分页参数、错误结构、Bearer scheme，以及启动/迁移/后端/前端/E2E 命令和敏感信息检查。

## 结论

确认 `RED_CONFIRMED`。schema 入口/生成命令和开发运行文档存在业务交付缺口，应回流实现/文档阶段补齐。
