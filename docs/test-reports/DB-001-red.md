# DB-001 RED

- 状态：`RED_CONFIRMED`
- 测试角色：测试 Agent
- 任务单：`docs/tasks/DB-001.md`
- 环境：Windows；`uv 0.7.21`；`uv run` Python `3.11.13`
- 环境判定：不是工具缺失阻塞。`uv sync --frozen --group test` 成功，公开 `manage.py` 命令可启动，pytest 可正常收集和执行测试。
- 命令：
  - `uv python install`
  - `Set-Location backend; uv sync --frozen --group test`
  - `uv run --project backend --group test --no-sync pytest backend/tests/test_db_001.py --tb=no -q`
  - `uv run --no-sync python manage.py check`
  - `uv run --no-sync python manage.py makemigrations --check --dry-run`
  - `uv run --no-sync python manage.py migrate --plan`
  - `uv run --no-sync python manage.py shell -c "...公开数据库探针..."`
- 通过 / 失败：DB-001 新增测试 `2 / 3`；新增测试输出 `3 failed, 2 passed`。
- 公开输入：`backend/pyproject.toml`、`backend/uv.lock`、`DATABASE_URL` 环境变量、Django `manage.py check`/迁移命令/测试命令和 `/api/v1/health/` JSON API。
- 期望行为：后端锁定 Django、DRF、JWT 黑名单和 PostgreSQL 驱动；Django 依据 `DATABASE_URL` 使用 PostgreSQL；测试数据库与开发数据库隔离；公开检查、迁移和测试数据库准备命令可运行；健康 API 返回 JSON。
- 实际行为：
  - `backend/pyproject.toml` 和 `backend/uv.lock` 仅包含 Django，缺少 `djangorestframework`、`djangorestframework-simplejwt` 和 PostgreSQL 驱动依赖。
  - `DATABASE_URL` 未设置；公开 Django 数据库探针返回 `connection=ok`、`vendor=sqlite`、`engine=django.db.backends.sqlite3`，目标为 `backend/db.sqlite3`，违反不得静默回退 SQLite 的契约。
  - 测试数据库准备测试在确认 PostgreSQL 前安全停止，没有对 SQLite 或未知开发库执行写入迁移；该失败由上述数据库后端契约失败触发，不是环境工具错误。
  - `manage.py check`、`makemigrations --check --dry-run`、`migrate --plan` 均退出码 0；这只能证明命令入口可启动，不能替代 PostgreSQL 基线验证。
  - `/api/v1/health/` JSON 基础测试通过。
- 是否稳定复现：是；数据库探针直接、确定地返回 SQLite，且新增测试失败点与公开配置缺失一致。
- 回归结果：健康 API 基线测试通过；本任务未读取或分析生产实现目录。
- 覆盖的验收标准：Django/DRF/JWT/PostgreSQL 依赖锁定、PostgreSQL 后端选择、DATABASE_URL 约束、测试数据库隔离、公开 check/迁移命令、API JSON 基础配置。
- 未覆盖风险：真实 PostgreSQL 测试数据库迁移尚未执行，因为当前配置会落到 SQLite；实现 Agent 补齐 PostgreSQL 配置和依赖后，需重新运行本测试并执行真实 PostgreSQL 测试库准备。
- 黑盒声明：测试只读取公开依赖配置、锁文件、环境变量和公开命令/API 输出，未读取或分析 `backend/apps/`、`backend/config/` 或 `frontend/src/`。

## 交接

- 当前状态：`RED_CONFIRMED`
- 接收角色：实现 Agent
- 实现范围：补齐任务单允许的 Django/DRF/JWT/PostgreSQL 依赖与公开数据库配置、测试数据库隔离和迁移基线；不得修改测试以绕过 PostgreSQL 断言。
- 建议复测命令：`uv run --project backend --group test --no-sync pytest backend/tests/test_db_001.py --tb=no -q`
