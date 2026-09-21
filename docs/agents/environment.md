# uv 与 nvm 环境规范

触发：安装依赖、切换 Python/Node.js、运行开发服务、测试、构建、迁移或 CI。

## 单一真相源

| 环境 | 管理工具 | 版本来源 | 依赖锁定 |
|---|---|---|---|
| Python | `uv` | 根目录 `.python-version` 与 `backend/pyproject.toml` 的 `requires-python` | `backend/uv.lock` |
| Node.js | `nvm` | 根目录 `.nvmrc` 与 `frontend/package.json` 的 `engines.node` | `frontend/package-lock.json` |

版本文件和锁文件是环境事实。文档只解释工作流，不复制具体版本号；切换版本时在同一任务中同步对应版本声明、锁文件和 CI 配置。

## Python：uv

进入后端工作前：

```powershell
uv python install
Set-Location backend
uv sync --frozen
```

日常命令统一经 `uv run` 执行：

```powershell
uv run python manage.py migrate
uv run python manage.py runserver
uv run pytest --tb=no
uv run ruff check .
```

依赖变更使用：

```powershell
uv add <运行时依赖>
uv add --dev <开发或测试依赖>
uv lock
```

环境约束：

- `uv` 负责 Python 安装、虚拟环境、依赖解析、锁定和命令执行。
- 项目虚拟环境使用 `backend/.venv`，不提交 Git。
- 项目依赖声明在 `backend/pyproject.toml`；不维护并行的 `requirements.txt` 依赖源。
- 常规同步使用 `uv sync --frozen`，保证锁文件未被隐式改写；只有依赖变更任务更新 `uv.lock`。
- 使用 `uv run` 调用 Python 工具，避免依赖全局 Python 或手工激活的虚拟环境。

## Node.js：nvm

进入前端工作前先让 nvm 选择根目录 `.nvmrc` 指定的版本。

macOS/Linux：

```bash
nvm install
nvm use
cd frontend
npm ci
```

Windows nvm：读取 `.nvmrc` 中的版本，然后执行：

```powershell
nvm install <项目 Node.js 版本>
nvm use <项目 Node.js 版本>
Set-Location frontend
npm ci
```

日常命令通过 `package.json` scripts 执行：

```powershell
npm run dev
npm run test
npm run lint
npm run build
```

环境约束：

- `nvm` 是 Node.js 版本的唯一切换入口；不依赖机器当前默认 Node.js。
- 前端包使用 `npm` 和 `package-lock.json` 做可重复安装；CI 与本地优先使用 `npm ci`。
- 前端 CLI 作为项目依赖安装并由 `npm run` 调用，不依赖全局安装的 Vite、Vitest、ESLint 或 Playwright。
- Node.js 版本变更必须同步 `.nvmrc`、`engines.node`、锁文件验证和 CI。

## Agent 执行步骤

1. 从版本文件选择运行时，不根据机器已安装版本猜测。
2. 使用锁文件同步依赖；锁文件缺失或与声明冲突时，将任务标记为 `BLOCKED` 或交给负责依赖变更的实现 Agent。
3. 通过 `uv run` 或 `npm run` 执行命令。
4. 在测试报告或实现说明中记录实际 Python、uv、Node.js 和 npm 版本。

完成标准：运行时与版本文件一致，依赖与锁文件一致，命令不依赖未声明的全局包，交付报告包含实际环境版本。

