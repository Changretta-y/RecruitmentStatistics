# REL-SYNC-001 TEST_PASSED

- 测试角色：release_tests，原独立测试 Agent。
- 被测实现：`9d63472`；测试先行提交：`75027d3`。
- 环境：Windows，PowerShell 7.6.5，Git 2.46.1.windows.1；仅 PowerShell/Git，无 Python/Node 依赖安装或运行。
- 命令：`pwsh -NoProfile -File tests/e2e/rel_sync_001_publish.ps1`。
- 通过 / 失败：19 / 0；退出码 0，输出 `RESULT passed=19 failed=0 fixtureOnly=False`。
- 公开输入：独立临时源仓库与本地 bare github/deploy/third 远端；已提交目标 SHA、脏文件、多 pushurl、自定义参数、受控 receive hooks、各类异常远端配置。
- 期望行为：GitHub 同步及 SHA 核对成功后才部署相同 SHA；明确 fetch URL、防止隐式双 pushurl 发布；非强制推送；失败阻断或保留部分完成并支持重跑；配置门禁与 DryRun 无远端变更。
- 实际行为：全部断言符合公开契约；成功 receive 顺序为 GitHub 后部署；双端 release 均精确等于捕获 SHA；第三仓库、stable 分支及未提交内容保留。
- 是否稳定复现：一次完整独立复测全部通过；拒绝、非快进与读回不一致均由真实本地 Git refs 和 hooks 观察，无生产实现 mock。
- 回归结果：同一套件覆盖发布相邻正常/异常行为；`git diff -- tests/e2e/rel_sync_001_publish.ps1` 无输出，先行测试和断言未经修改。无业务代码变更，因此不重复无关业务测试。
- 黑盒声明：未读取或分析入口或业务生产实现；入口仅作为不透明可执行文件复制到各临时调用仓库，通过退出码、stdout/stderr、Git refs 与 hook 事件核对。真实远端未访问，Git 仅允许 file 协议且禁用系统/全局配置；测试完成后精确临时目录安全清理。

## 覆盖的验收标准

| 公开行为 | 结果 |
| --- | --- |
| Git/PowerShell、本地拒绝与核对差异夹具 | PASS |
| 发布入口存在 | PASS |
| 双端同 SHA、GitHub receive 在先、脏文件与无关 refs 保留 | PASS |
| 多 origin pushurl 忽略且配置保留、第三仓库不更新 | PASS |
| 自定义 GitHubRemote 与 DeployRemote 参数 | PASS |
| GitHub 拒绝、非快进、读回不一致均阻断部署 | 3 PASS |
| 部署非快进不强推 | PASS |
| 部署拒绝保留 GitHub 已同步、提示重跑且重跑恢复 | PASS |
| 部署读回不一致返回失败 | PASS |
| DryRun 输出 SHA 与顺序计划、不执行 push | PASS |
| 非 release、游离 HEAD、两侧缺失、两侧多 fetch URL、相同目的均 push 前失败 | 7 PASS |

- 未覆盖风险：真实 GitHub/SSH 鉴权与凭据脱敏、README 发布文字、Jenkins 精确 revision SUCCESS、独立线上 health 尚待 PM 真实发布及同一测试角色只读线上复核；本地测试不模拟网络故障或并发远端变更。

## Agent 交接

- 任务编号：REL-SYNC-001。
- 当前状态：TEST_PASSED（本地发布入口测试）。
- 发送角色：测试 Agent release_tests。
- 接收角色：项目管理 Agent。
- 已完成内容与产物：先行黑盒套件 19/0、RED 与本独立通过报告齐全。
- 接收方工作范围：按任务单验收本地行为、使用说明并实际同步 GitHub 与部署；真实 push 仅由 PM 执行。
- 后续完成条件：Jenkins SUCCESS 与精确 revision 确认后，交回同一测试角色进行独立只读线上健康核对；PM 收齐证据后验收 DONE。
