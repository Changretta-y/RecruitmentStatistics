# DOC-001 独立复测报告

## 状态

TEST_PASSED

## 环境

- 工作目录：`G:\job`
- 后端：uv，PostgreSQL `127.0.0.1:5432`
- `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- 前端：Node 20.19.0、npm 10.8.2
- 测试 secret：仅用于测试进程的长 secret，未写入 README 或生产配置

## 环境命令

```text
cd backend
uv sync --frozen --group test
```

结果：`Audited 26 packages in 0.03ms`，成功。

```text
nvm use 20.19.0
cd frontend
npm ci
```

结果：安装成功；仅有 npm 依赖树的 engine warning，无命令失败。

## 测试命令与结果

```text
cd backend
uv run --no-sync pytest tests/docs/test_doc_001.py --tb=no -q
```

```text
4 passed in 0.37s
Exit code: 0
```

## 覆盖证据

- schema 公开入口或 `manage.py spectacular` 生成命令可用；
- 注册、登录、refresh、logout、me；
- 投递列表/新增/详情/修改/删除路径；
- 搜索、状态/阶段/时间、ordering、分页参数；
- 错误结构包含 `code`/`details` 与关键错误状态；
- OpenAPI Bearer HTTP security scheme；
- 启动、迁移、后端测试、nvm/npm、前端测试和 E2E 命令文档；
- 公开 README/开发部署文档不包含真实凭据、密码、Token 或生产地址。

本轮只修改测试报告/测试范围文件，未修改生产实现或 README。
