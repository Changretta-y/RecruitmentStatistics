# 上线工作流

触发：用户授权上线新版本、重跑部分完成的发布，或检查源码同步状态。

1. 按任务的 TDD 门禁取得独立 TEST_PASSED 与项目管理验收，单独提交本次发布文件。未提交内容保留，发布只包含当前 release 分支已提交 HEAD。
2. 在仓库根目录执行 `pwsh -File scripts/publish-release.ps1 -DryRun`，确认捕获 SHA 与 GitHub→部署的目的顺序。
3. 执行 `pwsh -File scripts/publish-release.ps1`。脚本先同步 GitHub 并核对 release SHA，再向部署仓库推送同一 SHA，最后核对两端一致。
4. 等待既有 Jenkins `RecruitmentStatistics-CI-CD` 对该 SHA 构建完成。成功条件为构建 SUCCESS、已完成、revision 等于捕获 SHA。
5. 独立测试角色只读核对构建、数据库备份元数据、容器健康、首页和 health API；项目管理记录真实上线结果。

完成条件：GitHub release、部署 release 与 Jenkins 成功构建 revision 均为本次捕获 SHA，独立线上健康检查通过。

## 错误恢复

- GitHub 同步或 SHA 核对失败：流程停止，解决权限、网络或分支冲突后重新执行入口。
- GitHub 已同步而部署推送失败：GitHub 保留已同步提交；解决部署远端问题后重跑入口。重跑同一 SHA 是幂等操作。
- 任一远端拒绝非快进更新：先核对并整合远端历史，再测试和发布。入口使用普通非强制推送。
- 两端同步完成而 Jenkins 失败：源码同步已完成，按 Jenkins 失败阶段处理；修复提交继续走相同入口。

脚本通过远端 fetch URL 明确选择目的仓库，避开 origin 多个 pushurl 的隐式推送。GitHub 标签和 Release 制品由单独需求定义。
