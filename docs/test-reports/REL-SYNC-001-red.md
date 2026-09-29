# REL-SYNC-001 RED_CONFIRMED

- 测试角色：release_tests，独立测试 Agent。
- 环境：Windows，PowerShell 7.6.5，Git 2.46.1.windows.1。仅调用 PowerShell/Git，不涉及 Python、uv、Node.js、npm 或安装依赖。
- 命令：`pwsh -NoProfile -File tests/e2e/rel_sync_001_publish.ps1 -FixtureOnly`；`pwsh -NoProfile -File tests/e2e/rel_sync_001_publish.ps1`。
- 通过 / 失败：夹具单跑 1 / 0，退出码 0；完整入口检查连续两次均 1 / 1，退出码 1。
- 公开输入：临时本地源仓库的 release 分支、github/deploy/third 三个 bare 仓库、两个明确 fetch URL、已提交目标 SHA。真实远端完全不使用，子进程仅允许 Git file 协议且禁用全局/系统配置。
- 期望行为：公开 `scripts/publish-release.ps1` 能在调用仓库当前目录运行，先同步 GitHub 并核对，再部署同一 SHA；非法配置及失败按任务契约阻断。
- 实际行为：`FAIL public release entry exists: Missing public scripts/publish-release.ps1 entry (required behavior absent)`。入口不存在，行为套件不调用缺失文件。
- 是否稳定复现：是，两次失败均为入口缺失；Git 夹具及子 PowerShell 已独立验证。测试开发时曾发现测试辅助函数与 git 命令同名的递归问题，已改为明确 git.exe 路径；该开发错误不计入 RED 证据。
- 夹具证据：本地 commit/push/ls-remote 成功；post-receive 事件记录先 GitHub 后 deploy；pre-receive 拒绝保持第三仓库原 ref；post-receive 改 release 后 ls-remote 可观察读回差异。每次使用独立随机任务临时根目录，退出时验证绝对路径、父目录与任务前缀后清理。
- 回归结果：发布入口缺失，因此尚无发布行为可回归；无业务/依赖变更，不运行无关业务套件。入口存在后同一脚本自动执行全部行为场景。
- 覆盖的验收标准：17 个公开行为场景，另含入口存在检查和夹具检查；成功同 SHA/receive 顺序；双 pushurl 忽略且保持原配置；自定义远端；GitHub hook 拒绝/non-fast-forward/读回不一致阻断；部署 non-fast-forward/hook 拒绝/读回不一致返回失败；部分完成后重跑恢复；DryRun；非 release、游离 HEAD、两侧缺失远端、两侧多 fetch URL、相同目的配置均 push 前失败；未提交文件与无关 stable refs 保留。
- 未覆盖风险：真实 GitHub/SSH 凭据、README 文字契约、真实 Jenkins 与线上健康，由 PM 及后续线上独立只读复测验收；本地 hook 不模拟网络故障或并发远端变更。输出检查要求 SHA、阶段标识与重跑提示，未使用真实凭据。
- 黑盒声明：未读取或分析生产实现代码；仅用 `Test-Path` 检查入口存在，后续将入口作为不透明可执行文件复制进隔离仓库，通过退出码、stdout/stderr、refs、hook 事件观察。

## Agent 交接

- 任务编号：REL-SYNC-001。
- 当前状态：RED_CONFIRMED。
- 发送角色：测试 Agent release_tests。
- 接收角色：PM，再由 PM 交给原实现 Agent。
- 已完成内容与产物：`tests/e2e/rel_sync_001_publish.ps1`、本 RED 报告；测试先行单独提交。
- 接收方工作范围：按任务单编写发布入口与使用说明，测试目录只读。
- 输入文档：`docs/tasks/REL-SYNC-001.md` 与本报告。
- 建议命令：`pwsh -NoProfile -File tests/e2e/rel_sync_001_publish.ps1`。
- 本阶段完成条件：可信入口缺失 RED 已确认，等待实现交付 READY_FOR_TEST 后由同一测试 Agent 独立复测。
