# E2E-001 TEST_FAILED

- 测试角色：测试 Agent
- 状态：**TEST_FAILED**
- 环境：Node 20.19.0、Playwright Desktop Chrome、前端 5182、后端 8000

## 实际命令

nvm use 20.19.0; E2E_BASE_URL=http://127.0.0.1:5182; E2E_API_URL=http://127.0.0.1:8000; E2E_RESTART_COMMAND=G:\job\tests\e2e\restart-backend.ps1; npm run e2e

## 结果

完整 7 流程：**6 passed、1 failed，退出码 1**。

前 6 项通过：注册/登录/列表、新增刷新持久化与阶段设置/清空、搜索筛选排序分页、删除、Access refresh/退出/旧 refresh 失效、双用户隔离。

第 7 项 backend restart 持久化失败。restart-backend.ps1 已改为在启动段显式设置测试环境的 Django secret、数据库 URL、DEBUG 和 CORS 变量，并移除 Start-Process -Environment，改为临时设置脚本进程环境后启动 uv，再恢复原值。但 node:child_process.execFileSync 在 45 秒受控超时内仍未返回，实际错误为：spawnSync pwsh.exe ETIMEDOUT。

## 证据

本轮结束时 restart-backend.ps1 存在（Test-Path=True）。Playwright restart 失败证据位于 test-results/e2e_001-E2E-001-core-publi-339ea-ves-application-persistence/，包含 restart-command-error、截图、视频和 trace。

该结果没有证明重启持久化业务失败，也没有满足 7 passed 条件；不能写入 TEST_PASSED。脚本文件、测试逻辑和报告均限于测试目录/测试报告目录。

- 黑盒声明：未读取或分析生产实现代码；仅观察公开 HTTP、Playwright 输出和测试辅助脚本状态。
