# EXT-ROUTE-002 TEST_PASSED

- 测试角色：原独立测试 Agent（company_tests），未承担生产实现。
- 状态：`TEST_PASSED`；提交项目管理 Agent 验收。
- 输入：测试先行提交 `13ad904` 与 RED 报告；实现 Agent `660787d`，状态 `READY_FOR_TEST`。从公开 ZIP 加载扩展，不读取插件生产源码。
- 环境：Windows；Node.js 20.19.0、npm 10.8.2；`uv` 0.7.21/Python 3.11.13 用于交付包解压；Playwright 加载 Edge/Chromium 扩展，本机 HTTP 替身隔离 API，不使用真实账号或生产服务。
- 本次被测 ZIP SHA-256：`220074BBFCD5D8FD6FF80F587C45EF7A28340198DFA4EFFF824E5C94FF9D45EA`。

## 独立命令与结果

在仓库根目录，使用 `.nvmrc` 的 Node 版本及锁定依赖：

```powershell
npm exec -- playwright test --config=tests/e2e/playwright.ext_route_002.config.ts
npm exec -- playwright test --config=tests/e2e/playwright.ext_route_001.config.ts
```

- EXT-ROUTE-002 专项：首次独立复测 **7/7 通过，33.0 秒**。为把“同名岗位必须提示选择/明确新建”从仅无 PATCH 的消极断言补全为弹窗可见正向断言，测试 Agent 只加强该断言，定向 1/1 通过，随后完整专项再跑 **7/7 通过，32.4 秒**；没有删除或放宽旧断言。
- EXT-ROUTE-001 URL/hash 相邻回归：**7/7 通过，39.0 秒**，覆盖路径、hash 内部 query、非追踪 query、追踪参数清理、新建/更新请求 URL 和非 HTTP(S) 边界。
- 两组均 exit 0，无浏览器、夹具、认证或网络环境错误。

## 与 RED 对照的公开行为

- 原相同 URL 不同岗位发 PATCH；现弹窗新建预览后只发 `POST /api/v1/applications/`，请求中保留当前链接和新岗位名，本机公开 API 替身返回含旧岗位与新增岗位的聚合，旧岗位 ID/备注不变。
- 原已有两条同公司同名岗位时未经选择直接 PATCH；现弹窗可见选择/多条/新建提示，没有随机 PATCH/PUT，两条原岗位备注保持不变。
- 同公司同岗位更新仍发目标公司聚合的 PATCH，URL 变化被放进公开请求 JSON；公司与岗位名去空白/大小写规范化后仍命中。
- 同公司不同岗位且 URL 不同继续 POST；`utm_*` 等追踪参数移除，普通 query 与 hash 路由保留。
- 错误密码和缺失公司/岗位输入均不发送应用写请求；原 EXT-ROUTE-001 深层 URL/hash 行为不回退。

## 风险与交接

- API 是本机合同替身；本报告只确认可加载插件的预览和请求选择。真实平台持久化新旧岗位由 APP-009/APP-012 已有独立 API/端到端证据及项目管理验收核对，不把替身的聚合状态冒充生产写入证明。
- APP-012 当前不接受 nested 岗位的 `application_url` 写入，非首岗位单独链接更新的真实持久化另属后端契约范围。实现说明称插件对此给出不支持提示；本专项没有通过真实后端验证该提示或持久化。此已知限制不影响本任务“同公司不同岗位不得被旧 URL 覆盖”的修复结论。
- 项目管理 Agent 可根据任务单、RED、实现说明及本报告进入 `ACCEPTING`；仅项目管理 Agent 可设置 `DONE`。

## 黑盒声明

未读取、搜索或分析 `frontend/src/`、`backend/apps/`、生产配置或插件 ZIP 内源码。复测观察可加载扩展的弹窗与本机 HTTP 替身所接收的公开方法、路径和 JSON；未修改生产实现、后端数据或其他角色交付物。
