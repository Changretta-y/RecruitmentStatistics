# BASE-ENV-001 使用 uv 与 nvm 管理开发环境

- 状态：`DONE`
- 负责拆解：项目管理 Agent
- 用户价值：所有开发、测试和 CI 使用一致且可复现的 Python 与 Node.js 环境。
- 范围：Python/Node.js 版本声明、依赖管理、锁文件、忽略规则、环境验证和使用说明。
- 非范围：业务功能、数据库业务模型、认证接口、页面功能。
- 依赖：无；应在其他工程任务前完成。
- 允许实现范围：根目录版本文件、`backend/pyproject.toml`、`backend/uv.lock`、`frontend/package.json`、`frontend/package-lock.json`、`.gitignore`、CI 环境配置。

## 业务规则与公开契约

1. Python 环境只通过 `uv` 创建、同步和执行。
2. Python 版本由 `.python-version` 与 `backend/pyproject.toml` 一致声明，依赖由 `backend/uv.lock` 锁定。
3. Node.js 版本只通过 `nvm` 切换，由 `.nvmrc` 与 `frontend/package.json#engines.node` 一致声明。
4. 前端依赖由 `frontend/package-lock.json` 锁定，并使用 `npm ci` 做可重复安装。
5. Python 工具通过 `uv run` 执行，前端工具通过 `npm run` 执行；项目不依赖全局业务 CLI。
6. `.venv`、`node_modules` 和本地密钥文件进入 Git 忽略规则，版本文件与锁文件提交 Git。

## 输入、输出与错误行为

- 输入：一份全新检出的仓库，以及已安装的 `uv`、`nvm` 和 PostgreSQL。
- 输出：按版本文件选择运行时后，可仅凭锁文件完成前后端依赖安装。
- 版本文件不一致：环境验证失败并指出冲突字段。
- 锁文件与依赖声明不一致：冻结同步或 CI 失败，不自动重写锁文件。
- 运行时未安装：给出通过 `uv python install` 或 `nvm install` 安装项目版本的提示。

## 验收标准

- [ ] 全新环境可依据 `.python-version` 创建 Python，并在 `backend/` 执行 `uv sync --frozen`。
- [ ] 后端测试、迁移和开发命令均能通过 `uv run` 启动。
- [ ] 全新环境可依据 `.nvmrc` 用 nvm 安装并切换 Node.js。
- [ ] `frontend/package.json#engines.node` 与 `.nvmrc` 表达同一 Node.js 版本约束。
- [ ] 在 `frontend/` 执行 `npm ci` 后，测试、检查和构建脚本可启动。
- [ ] `.venv` 与 `node_modules` 不被 Git 跟踪，版本文件及两个锁文件被跟踪。
- [ ] CI 使用同一 Python/Node.js 版本和冻结依赖安装方式。
- [ ] 环境验证对版本不一致和过期锁文件给出失败结果。

## 风险与测试边界

- Windows nvm 与 macOS/Linux nvm 的命令入口不同，测试应验证版本结果而不是绑定某一种 shell 实现。
- `uv sync --frozen` 和 `npm ci` 需要锁文件预先存在；初始化锁文件属于实现步骤，不应在复测时隐式更新。
- 测试只验证公开命令、版本输出、锁文件一致性和 Git 跟踪结果，不读取业务实现代码。
## 状态历史

- `PLANNED`：项目管理 Agent 创建任务单。
- `RED_CONFIRMED`：测试 Agent 证明工程基线公开契约缺失。
- `IMPLEMENTING` → `READY_FOR_TEST`：实现 Agent 补齐版本文件、依赖锁定、前端配置、忽略规则和 CI。
- `BLOCKED`：此前验收因宿主机缺少 nvm、无法验证 `.nvmrc` 指定的 Node.js 版本；该阻塞记录保留为历史。
- `TEST_PASSED`：独立复测确认 uv/nvm 版本、冻结安装、后端联合测试、前端 npm 流程、版本/锁文件、CI 和 Git 跟踪契约全部通过。
- `DONE`：项目管理 Agent 于 2026-09-20 完成最终验收。
