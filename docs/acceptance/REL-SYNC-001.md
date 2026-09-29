# REL-SYNC-001 验收记录

- 状态：ACCEPTING
- 角色：项目管理 Agent（主 Agent）。
- 任务单：docs/tasks/REL-SYNC-001.md。
- RED：docs/test-reports/REL-SYNC-001-red.md，测试先行提交 75027d3。
- 实现说明：docs/implementation-notes/REL-SYNC-001.md，实现提交 9d63472。
- 独立 TEST_PASSED：docs/test-reports/REL-SYNC-001-passed.md，提交 b51e4ec。
- 环境：Windows PowerShell 7.6.5、Git 2.46.1；真实 origin/deploy 配置与现有 release 分支。

## 标准与证据

- [x] 双端同 SHA、GitHub 先于部署：原测试角色隔离仓库 refs 与 receive 事件独立通过。
- [x] origin 多 pushurl 绕过：第三仓库不更新、原配置不修改，独立通过。
- [x] GitHub 拒绝、非快进、读回差异阻断部署：退出非零、deploy 保持原值，独立通过。
- [x] 部署失败与重跑：GitHub 保留提交，报告阶段与恢复提示；解除拒绝后两端同 SHA，独立通过。
- [x] 配置、分支门禁和 DryRun：非法输入 push 前停止；DryRun 不写 refs，独立通过。PM 在真实仓库执行 DryRun，退出 0，捕获已提交 SHA 并展示 GitHub→部署→双端核对顺序。
- [x] 工作区和其他 refs 保留：隔离测试验证未提交文件不进入提交、无关 stable 分支不变；真实仓库无关脏文件未提交或清理。
- [x] 持久入口：README 的“新版本上线”列出 `pwsh -NoProfile -File scripts/publish-release.ps1` 与预演及重跑条件，链接 docs/requirements/release-workflow.md；需求索引已提供触发指针。
- [x] 角色交付齐全：独立 RED、测试先行、独立实现、自检说明和原测试 TEST_PASSED 存在；19项全通过，没有修改断言或质量门槛。
- [ ] 真实 GitHub 与部署 release 同 SHA、Jenkins SUCCESS 精确 revision、独立线上健康核对。

## 结论

本地契约验收通过，等待真实发布与独立只读线上复核后设置 DONE。GitHub 当前落后但为本地 HEAD 的祖先；既有 Jenkins 从部署 bare repo 的 release 读取 Jenkinsfile，最近 #15 SUCCESS，发布前首页与 health HTTP 200。
