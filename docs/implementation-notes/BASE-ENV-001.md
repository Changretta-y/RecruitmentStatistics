# BASE-ENV-001 实现说明

- 状态：READY_FOR_TEST
- 修改范围：根目录 Python/Node.js 版本声明、`.gitignore`、`frontend/package.json`、`frontend/package-lock.json`、`.github/workflows/ci.yml`；未修改测试、测试报告或上级 `G:/bk-incident/pyproject.toml`。
- 已实现行为：Python 通过根目录 `.python-version` 和后端 `pyproject.toml` 约束，后端依赖由 `backend/uv.lock` 冻结；Node.js 通过 `.nvmrc` 与 `frontend/package.json#engines.node` 约束；前端锁文件可供 `npm ci` 使用；本地环境文件、虚拟环境和依赖目录被 Git 忽略；CI 使用声明的 Python/Node.js 版本、`uv sync --frozen`、`uv run`、`npm ci` 和 `npm run`。
- 数据库迁移：无。
- 配置变化：`.python-version=3.11.13`；`.nvmrc=20.19.0`；前端当前为无运行时依赖的可安装基线，测试、检查和构建脚本均可通过 `npm run` 启动。
- 已知限制：当前主机未安装 `nvm` 时不伪造 nvm 切换验证；`.nvmrc` 和 `engines.node` 已保持一致，需在具备 nvm 的环境执行 `nvm install`/`nvm use` 后进行真实 Node.js 版本验证。当前前端尚未进入 Vue 页面功能任务。
- 自检结果：真实版本为 Python 3.12.7（主机默认）、uv 0.7.21、Node.js v24.16.0、npm 11.13.0；`uv python install`、`uv lock --project backend --check`、`uv sync --project backend --frozen --group test`、`uv run --project backend pytest backend/tests/test_health.py backend/tests/test_urls.py --tb=no -q`（2 passed）、`uv run python manage.py check`（无问题）、`npm ci --prefix frontend --ignore-scripts --no-audit --no-fund --dry-run` 和三个 `npm run` 脚本均成功。BASE-ENV-001 环境测试在临时 Git 安全目录配置下为 6 passed、1 failed；唯一失败是测试通过 Python `subprocess` 启动 `npm` 时命中了宿主机无扩展名的 `npm` 脚本，Windows `CreateProcess` 返回 WinError 2，非 package-lock 解析失败。主机未安装 nvm，未伪造 nvm 验证。
- 建议复测命令：`uv python install`; `uv sync --project backend --frozen --group test`; `uv run --project backend pytest backend/tests/test_base_env_001.py backend/tests/test_health.py backend/tests/test_urls.py --tb=no -q`; 在 nvm 可用环境执行 `nvm install`、`nvm use`、`npm ci --prefix frontend --ignore-scripts --no-audit --no-fund --dry-run`、`npm run test --prefix frontend`、`npm run lint --prefix frontend`、`npm run build --prefix frontend`。
- 测试完整性声明：未修改测试、断言或质量门槛。
