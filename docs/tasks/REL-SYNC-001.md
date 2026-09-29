# REL-SYNC-001 上线前同步 GitHub

- 状态：TEST_WRITING
- 项目管理角色：主 Agent；测试角色：release_tests；实现角色：release_implementation。每个 Agent 只承担此单一角色。
- 用户价值：每个上线版本的源码提交同时保存在 GitHub，避免只推服务器造成仓库落后。
- 范围：统一 PowerShell 发布入口、使用说明、独立本地 Git 黑盒测试；验收后由 PM 使用入口同步本次提交并触发既有 Jenkins。
- 非范围：业务代码、Jenkins 内部部署步骤、GitHub Release/tag、凭据创建、强制推送、历史重写、无关工作区改动。
- 输入：用户“现在修改上线工作流，新版本也要同步更新到github”；系统设计第 15–16 节；DEPLOY-001/DEPLOY-SHARE-001 的部署契约。
- 允许修改范围：PM 仅 docs/tasks/、docs/requirements/、docs/acceptance/；测试仅 tests/e2e/、docs/test-reports/；实现仅 scripts/publish-release.ps1、README.md、docs/implementation-notes/REL-SYNC-001.md（上线运行入口与生产使用说明）。
- 环境：执行脚本先读 docs/agents/environment.md；仅 PowerShell/Git 的测试无需安装 Python/Node 依赖。

## 业务规则与公开契约

新增 scripts/publish-release.ps1；在发布仓库当前工作目录调用，默认远端 GitHubRemote=origin、DeployRemote=deploy，可通过同名参数替换为隔离本地测试远端。只接受当前 release 分支，捕获已提交 HEAD 的完整 SHA；即使存在未提交文件也只发布已提交 SHA，不替用户提交/清理文件。

默认执行顺序：解析两个远端的单一 fetch URL（避免 origin 的双 pushurl 隐式发布）；所有配置验证完成后，先以明确的 SHA:refs/heads/release 非强制推送 GitHub URL；ls-remote 核对 GitHub release 等于捕获 SHA；随后非强制推送同一 SHA 到部署 URL，并核对两端 release 都等于捕获 SHA。错误返回非零，GitHub 推送/核对失败时部署远端不得更新。部署失败时保留 GitHub 已同步状态，输出可重跑提示；重跑不会回退历史。

- 两个远端必须存在，各自只允许一个 fetch URL，且两个目的 URL 必须不同；配置歧义在任何 push 前失败。
- 支持 -DryRun：仅输出捕获 SHA 与 GitHub→部署的计划，不执行 push 或修改远端。
- 输出包含捕获 SHA、各阶段成功/失败以及双端核对结果，不打印凭据。
- README 在上线章节列出唯一入口及错误恢复说明；正式上线按 GitHub 同步→部署推送→等待 Jenkins SUCCESS/精确 revision→独立线上健康核对执行。
- PM 的持久发布契约保存在 docs/requirements/release-workflow.md，README 链接该契约。以后用户授权上线时按此入口执行。
- 不修改 remote.origin.pushurl，本入口用明确 URL 保证顺序。

## 验收标准

- [ ] 隔离本地 Git 仓库：发布将 GitHub 与部署 release 都更新为捕获的同一提交；GitHub receive 先于部署 receive。
- [ ] origin 即使有指向第三仓库/部署的多个 pushurl，入口也只按两个 fetch URL 的明确顺序推送，不更新第三仓库。
- [ ] GitHub 拒绝/non-fast-forward 或核对失败时，入口非零退出，部署 release 原值不变。
- [ ] 部署拒绝时清晰报告部分完成；移除拒绝因素重跑，两端一致，不强推。
- [ ] 非 release/游离 HEAD、缺失/歧义/相同目的配置在 push 前失败；DryRun 不改变远端。
- [ ] 未提交文件保留且不进入推送提交，其他远端分支不变。
- [ ] 测试先行提交、RED、实现说明、TEST_PASSED、验收记录齐全。
- [ ] 本次已验收提交实际同步到 GitHub release 和部署 release；既有 Jenkins 精确 revision SUCCESS 与线上 health 正常。

## 风险与测试边界

测试 Agent 只从参数、退出码、stdout/stderr、隔离仓库公开 Git refs/hook 事件观察行为，不读取 scripts/ 或业务实现。测试不得触碰真实远端。PM 的真实推送沿用现有 Git/SSH 授权，不读取 env、密钥或完整服务器日志。现有未提交资料均保留，仅本任务产物单独提交。

## Agent 交接

- 任务编号：REL-SYNC-001
- 当前状态：PLANNED
- 发送角色：PM
- 接收角色：release_tests
- 输入：本任务、系统设计第 15–16 节、environment.md、test-agent.md、workflow.md、templates.md。
- 本阶段完成条件：独立黑盒测试与稳定 RED（入口缺失属于缺失行为，环境和夹具已验证），仅提交测试和 RED 报告，再交给 PM。
