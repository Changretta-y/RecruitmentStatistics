# E2E-001 独立复测报告

- 测试角色：测试 Agent
- 状态：**TEST_PASSED**
- 环境：Node 20.19.0、Playwright Desktop Chrome、前端 http://127.0.0.1:5182、后端 http://127.0.0.1:8000

## Node 重启脚本独立验证

先使用 Node child_process.execFileSync 调用 G:\job\tests\e2e\restart-backend.ps1，超时 45 秒；本轮返回成功，输出确认停止本地 backend PID、启动 server PID 并 health status 200。

重启脚本启动段显式设置测试环境的 Django secret、DATABASE_URL、DEBUG 和 CORS 变量，启动后端后再恢复脚本进程原值；不依赖测试运行器继承，也未使用 Start-Process -Environment 覆盖环境。停止阶段仍只匹配本地 G:\job\backend 与 manage.py runserver 127.0.0.1:8000。

## 完整 E2E 命令与结果

命令：

nvm use 20.19.0; E2E_BASE_URL=http://127.0.0.1:5182; E2E_API_URL=http://127.0.0.1:8000; E2E_RESTART_COMMAND=G:\job\tests\e2e\restart-backend.ps1; npm run e2e

结果：**7 passed，34.3s，退出码 0**。

## 流程覆盖

1. 注册、登录并进入本人投递列表：passed。
2. 新增、reload 持久化、阶段设置与清空：passed；诊断 GET 200 的 results 包含目标记录。
3. 多记录搜索、筛选、排序、分页和 page size：passed。
4. 删除取消/确认及列表更新：passed。
5. Access 过期单次 refresh、退出及旧 refresh 失效：passed；refresh 次数恰好 1 次。
6. 双用户数据隔离：passed。
7. 实际服务重启后持久化：passed；restart-backend.ps1 已执行，重启后 applications GET/页面仍包含重启前创建的“E2E 重启持久化公司”。

执行结束确认：restart-backend.ps1 Test-Path=True。

## 未覆盖风险

本次验证覆盖本地开发服务和 Desktop Chrome；未覆盖生产部署编排器、非 Chromium 浏览器及多实例/负载均衡场景。通过报告不包含真实密钥或数据库凭据。

- 黑盒声明：未读取或分析生产实现代码；仅观察公开 HTTP/UI、Playwright 结果和测试辅助脚本行为。
