# REL-SYNC-001 实现说明

- 状态：READY_FOR_TEST。
- 实现角色：release_implementation；输入为任务单与 `75027d3` 的独立 RED 证据。
- 修改范围：`scripts/publish-release.ps1`、`README.md`、本说明。
- 已实现行为：按调用工作目录读取 release 分支的已提交 HEAD；先验证两个远端的单一且不同 fetch URL；明确非强制推送捕获 SHA 到 GitHub，读回核对成功后再推 deploy，最后双端读回核对。origin pushurl、未提交文件和其他 refs 均不修改。支持 DryRun 和自定义远端参数。
- 错误行为：原生 Git 输出在内存捕获并逐次检查退出码，兼容 Windows PowerShell 的 stderr ErrorRecord 与 pwsh 原生错误偏好；公开失败输出仅含固定阶段、退出码和捕获 SHA，不回显 URL、凭据或远端 hook 原文。部署阶段失败保留 GitHub 状态并提示重跑。
- 数据库迁移：无。
- 配置变化：无 Git remote 或运行时配置修改；README 指向持久上线契约，并规定新版本统一使用入口。
- 已知限制：双端顺序推送不具备分布式事务；并发远端修改可能导致核对失败，需处理后重跑。入口只负责源码同步；既有 Jenkins revision 和线上健康仍需独立确认。未使用真实远端做自检。
- 环境：PowerShell 7.6.5、Windows PowerShell 5.1.22621.4249、Git 2.46.1.windows.1；无需 Python/Node 依赖。
- 自检结果：`pwsh -NoProfile -File tests/e2e/rel_sync_001_publish.ps1` 为 19 passed / 0 failed，退出码 0。首次自检发现 PATH 中多份 Git 导致可执行文件解析成数组，已修正为选择首个 Application 并完整重跑通过。Windows PowerShell 5.1 的真实仓库 DryRun 为退出码 0，非 Git 目录的 native 128 失败被入口转换为退出码 1、未回显原始 stderr。自检不代替独立复测。
- 建议复测命令：`pwsh -NoProfile -File tests/e2e/rel_sync_001_publish.ps1`。
- 测试完整性声明：未修改测试、断言或质量门槛。

## Agent 交接

- 任务编号：REL-SYNC-001；当前状态：READY_FOR_TEST。
- 发送角色：release_implementation；接收角色：PM，转交原测试角色 release_tests。
- 已完成内容与产物：发布入口、README 使用及恢复说明、本说明；实现独立提交在测试先行提交之后。
- 接收方工作范围：仅从公开参数、退出码、输出和隔离 Git refs 独立复测；建议使用上述命令。
- 结果或风险：本地自检通过；真实 GitHub、部署、Jenkins 和线上健康尚待 PM 调度验收。
- 本阶段完成条件：由原测试角色提供独立 TEST_PASSED 或失败回流报告。
