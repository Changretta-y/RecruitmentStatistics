# REL-001 RED 测试报告

## 状态

RED_CONFIRMED

## 测试角色与边界

- 测试角色：测试 Agent
- 工作目录：`G:\job`
- 新增黑盒测试：`backend/tests/test_rel_001.py`
- 允许修改范围内仅修改了 `backend/tests/` 与 `docs/test-reports/`
- 未读取或修改 `backend/apps/`、`backend/config/`、`frontend/src/` 或 CI 配置
- 检查对象是锁定命令环境、公开测试/构建命令和公开 HTTP API；未用生产源码断言代替行为测试

## 环境与已执行命令

运行时与依赖：

```text
.python-version = 3.11.13
.nvmrc = 20.19.0
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres
uv sync --frozen --group test                         # 成功
```

专项 RED：

```text
Set-Location G:\job\backend
uv run --no-sync pytest tests/test_rel_001.py --tb=no -q
```

结果：

```text
.FF                                                                      [100%]
2 failed, 1 passed in 4.95s
Exit code: 1
```

## RED 失败证据

### 1. 后端 coverage 门禁工具未锁定

Ruff 已可运行，但 coverage 命令在 `uv sync --frozen --group test` 后不存在：

```text
uv run --no-sync ruff --version
ruff 0.11.4

uv run --no-sync coverage --version
error: Failed to spawn: `coverage`
Caused by: program not found
Exit code: 1
```

这不是测试语法、夹具或数据库错误：冻结依赖同步成功，Ruff 也已从同一环境执行；当前锁定测试依赖缺少可执行的 coverage 门禁，无法验证任务要求的后端总体 >=90% 及认证/权限/Token 分支阈值。因此专项测试稳定失败，确认一个发布质量门禁缺口。

### 2. 前端 coverage 门禁不可执行

前端公开测试命令在 Node 20.19.0 下明确报告缺依赖：

```text
nvm use 20.19.0
npx vitest --run --coverage --pool=threads --maxWorkers=1
 MISSING DEPENDENCY  Cannot find dependency '@vitest/coverage-v8'
Exit code: 1
```

专项测试同时检查 `frontend/vitest.config.mts` 的公开 coverage 配置，断言失败；当前配置只有 `test.environment`，没有 coverage 配置或阈值。该缺口使前端 >=80% 以及 Token/refresh/store 分支阈值无法成为可执行门禁，不是业务测试夹具错误。

## 已通过/已观察结果

- `uv run python manage.py check`：成功，`System check identified no issues (0 silenced)`。
- `uv run python manage.py migrate --plan`：成功，输出 `No planned migration operations.`。
- `backend/tests/test_rel_001.py` 的公开 smoke：通过；health 返回 `200`/`{"status":"ok"}`，注册返回成功或已存在的明确冲突，未认证投递列表返回 `401`。
- `frontend npm run lint`：成功。
- `frontend npm run build`：成功；Vite 输出 `✓ built in 239ms`。

## PostgreSQL 发布演练：BLOCKED（未计入 RED）

本轮没有把数据库演练失败伪装成业务 RED。当前执行器 PATH 中：

```text
psql      MISSING
pg_dump   MISSING
pg_restore MISSING
```

因此尚未实际执行隔离 PostgreSQL 空库迁移、升级路径、备份、恢复及恢复后数据核验；当前只完成了已有数据库上的 `migrate --plan` 预检。没有可安全使用的独立备份/恢复工具入口，也未伪造备份恢复结果。该部分状态为 `BLOCKED`，需要提供 PostgreSQL client 工具和隔离数据库目标后才能形成有效证据。

## 未执行或未宣称通过的发布门禁

- 完整 Ruff→pytest/coverage→ESLint/TypeScript→Vitest/coverage→build→E2E 的顺序编排：当前没有运行结果可宣称；本轮只执行了可独立验证的公开子命令。
- 后端完整 coverage 阈值、前端完整 coverage 阈值：因 coverage 工具/coverage-v8 缺失，未验证。
- PostgreSQL 空库/升级/备份/恢复实际演练：BLOCKED，未伪造结果。
- 完整浏览器 E2E：本报告阶段未重新运行，不引用历史结果替代本轮证据。

## 结论

`RED_CONFIRMED`：后端冻结测试环境缺少 coverage 可执行门禁，前端 coverage provider/configuration 缺失，均为 REL-001 发布质量契约的稳定缺口。数据库备份/恢复部分另记为 `BLOCKED`，不是 RED。未修改生产实现或 CI 配置。
