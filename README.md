# 校招进度管理系统

本项目由 Django/DRF 后端和 Vue 前端组成。版本事实以根目录的 `.python-version`、`.nvmrc`、`backend/pyproject.toml`、`backend/uv.lock` 和 `frontend/package-lock.json` 为准。

## 环境变量

后端启动前通过运行环境注入以下配置：

- `DJANGO_SECRET_KEY`：必需的随机长密钥；不要提交到仓库。
- `DATABASE_URL`：必需的 PostgreSQL 连接配置；缺失时不会回退 SQLite。
- `DJANGO_DEBUG`：生产必须为 `false`。
- `DJANGO_ENV=production`：启用生产 HTTPS、HSTS 和安全 Cookie 默认值。
- `CORS_ALLOWED_ORIGINS`：逗号分隔的显式前端来源，不允许 `*`。
- 可选安全项：`DJANGO_ALLOWED_HOSTS`、`SECURE_SSL_REDIRECT`、`SECURE_HSTS_SECONDS`、`SECURE_REFERRER_POLICY`。

请使用本地未提交的环境管理方式注入配置，不把密钥、凭据、Token 或生产地址写入文档或代码。

## 后端开发

```text
uv sync --frozen --group test
Set-Location backend
uv run python manage.py check
uv run python manage.py migrate
uv run python manage.py runserver
```

生产配置可用以下命令检查：

```text
uv run python manage.py check --deploy --fail-level WARNING
uv run python manage.py spectacular --file openapi.json --validate
```

OpenAPI 入口：

- `/api/schema/`：JSON/YAML schema。
- `/api/schema/swagger/`：Swagger UI。

公开 API 包括注册、登录、refresh、logout、me 和投递记录列表/创建/详情/PATCH/DELETE。投递列表支持搜索、状态/阶段/时间筛选、ordering、分页和 Bearer JWT 认证；错误响应使用统一 `code`/`details` 结构。

## 前端开发

```text
nvm use
Set-Location frontend
npm ci
npm run test
npm run build
```

前端通过统一 HTTP 层访问后端，不在页面代码中保存凭据。浏览器端到后端的地址和跨域来源由运行环境配置。

## 测试与 E2E

后端测试：

```text
Set-Location backend
uv run pytest --tb=no
```

前端测试和构建：

```text
Set-Location frontend
npm run test -- --run
npm run build
```

E2E 测试在后端和前端服务均按上述命令启动后执行：

```text
npm run e2e
```

若项目当前未配置 E2E runner，请由对应测试任务提供 runner 和浏览器依赖；本说明不替代 E2E 测试实现。

## Docker Compose 部署

项目提供了 PostgreSQL、Django 后端和 Nginx/Vuetify 前端的 Compose 编排。首次启动：

```text
docker compose up -d --build
```

启动后访问 `http://服务器地址:5173`。前端 Nginx 会将 `/api/` 请求转发到后端，后端容器启动时会自动执行数据库迁移。

部署到服务器前，建议通过服务器环境变量覆盖默认值，至少设置 `DJANGO_SECRET_KEY`、`POSTGRES_PASSWORD` 和 `DJANGO_ALLOWED_HOSTS`：

```text
ssh huoshan
cd /path/to/job
export DJANGO_SECRET_KEY='请替换为随机长密钥'
export POSTGRES_PASSWORD='请替换为数据库密码'
export DJANGO_ALLOWED_HOSTS='服务器域名或IP,localhost,127.0.0.1'
docker compose up -d --build
docker compose ps
```

查看日志：

```text
docker compose logs -f backend frontend
```
