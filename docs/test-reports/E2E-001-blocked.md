# E2E-001 BLOCKED

- 测试角色：测试 Agent
- 状态：**BLOCKED**
- 环境：Node 20.19.0、Playwright Desktop Chrome；前端 http://127.0.0.1:5182；后端 health 入口 http://127.0.0.1:8000/api/v1/health/
- 测试目录变更：新增 tests/e2e/restart-backend.ps1；restart 测试使用 node:child_process.execFileSync 执行 E2E_RESTART_COMMAND，超时 45 秒。

## 命令

nvm use 20.19.0; $env:E2E_BASE_URL='http://127.0.0.1:5182'; $env:E2E_API_URL='http://127.0.0.1:8000'; $env:E2E_RESTART_COMMAND='G:\job\tests\e2e\restart-backend.ps1'; npm run e2e

## 结果

完整 7 流程实际结果：**6 passed、1 failed，退出码 1**。

- 注册/登录/列表：passed
- 新增、刷新持久化、阶段设置/清空：passed
- 搜索/筛选/排序/分页：passed
- 删除取消/确认：passed
- Access refresh/退出/旧 refresh 失效：passed
- 双用户隔离：passed
- 强制服务重启持久化：未执行，安全重启脚本在匹配阶段阻塞

## 阻塞证据

restart-backend.ps1 的公开错误为：No backend process matched the exact safe restart command line.

脚本只允许匹配命令行精确包含 G:\job\backend\manage.py runserver 127.0.0.1:8000 的进程。当前可见的 8000 开发进程命令行使用相对路径 manage.py runserver 127.0.0.1:8000，未满足该精确安全条件，因此脚本没有停止任何进程，也没有启动新进程。拒绝后 health 仍为 200。

本轮未伪造重启通过结果，也未扩大匹配条件以停止其他进程。Playwright restart 失败证据位于 test-results/e2e_001-E2E-001-core-publi-339ea-ves-application-persistence/，包含 restart-command-error、截图、视频和 trace。

## 下一步解除条件

由环境编排器以命令行包含精确绝对路径的方式启动目标后端开发进程，再使用同一 E2E_RESTART_COMMAND 重跑完整 7 流程。未提供该进程前，不能安全执行强制重启验收。

- 黑盒声明：未读取或分析生产实现代码；仅观察公开 HTTP health 和本地进程命令行。
