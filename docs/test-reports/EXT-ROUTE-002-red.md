# EXT-ROUTE-002 RED_CONFIRMED

- 测试角色：测试 Agent（company_tests），仅负责公开黑盒测试与报告。
- 当前状态：`RED_CONFIRMED`；可交实现 Agent 修复插件保存匹配规则。
- 环境：Windows；`.nvmrc` 选择 Node.js v20.19.0，npm 10.8.2；根锁文件 `npm ci --no-audit --no-fund` 成功；`uv` 0.7.21、Python 3.11.13 用于解压交付 ZIP。Playwright 用已安装的 Edge/Chromium 加载 ZIP 中的扩展；本机 HTTP 替身隔离所有 `/api/` 请求，不访问生产服务或真实账号。
- 被测交付包：`artifacts/recruitment-capture-extension-v0.1.0.zip`，测试时 SHA-256 `628201B1C745D0B4AB4AC06A6622D03775C2BEB159FFD0EBE9D5BDA5CDBE8F9E`。仅作为可加载公开产物使用，未读取插件源码。

## 可复现命令与统计

仓库根目录，先按环境规范 `nvm use 20.19.0` 并 `npm ci`，然后：

```powershell
npm exec -- playwright test --config=tests/e2e/playwright.ext_route_002.config.ts
npm exec -- playwright test --config=tests/e2e/playwright.ext_route_001.config.ts
```

- 新专项最终完整运行：**2 failed / 5 passed / 0 环境错误，36.6 秒**。此前同两个缺失行为在完整运行中稳定复现（当时 2 failed / 4 passed，另一个旧输入校验用例尚未加入）；期间仅修复了测试自身点击不可用按钮导致的夹具超时。最终失败均为明确的 HTTP 方法断言。
- EXT-ROUTE-001 原 URL/hash 回归：**7 passed，36.1 秒**，覆盖 hash 内部 query、路径、追踪参数清理、更新请求 URL、非 HTTP(S) 页面。

## 公开输入、预期与实际

1. API 列表已有“黑盒公司 / 原岗位”，其招聘链接与当前页完全相同。弹窗填写同公司“新增岗位”，预览已显示新建语义。确认后应只发送 `POST /api/v1/applications/`，由 APP-009/APP-012 的公司聚合追加语义保留旧岗位及其备注。实际插件只发一个 `PATCH /api/v1/applications/701/`；断言 `Expected POST / Received PATCH`。失败不是浏览器、登录或 HTTP 替身错误。
2. API 聚合下已有两条同公司且同名“重复岗位”记录（不同岗位 ID、独立备注）。弹窗再次录入相同公司岗位时，契约要求提示选择或明确新建，不得随机覆盖一条。实际点击确认后发出 PATCH/PUT；断言 `Expected false / Received true`。
3. 同公司同岗位、URL 改变仍 PATCH 指定公司聚合；公司和岗位名称去空白/大小写规范化后仍命中；同公司不同岗位且不同 URL 走 POST 并保留 normalized URL/hash；错误密码无法写入；公司/岗位都空时不发送写请求。这五项已通过，说明 RED 仅针对错误匹配优先级和同名歧义。

## 覆盖与交接

- 测试仅通过可加载交付 ZIP、弹窗可见预览及本机 HTTP 替身记录的公开请求方法、路径、JSON 断言；在替身中模拟追加后的完整聚合以观察新旧岗位状态，不把替身结果当作真实后端持久化证明。后端真实追加契约由 APP-009/APP-012 独立测试覆盖。
- 测试文件：`tests/e2e/ext_route_002.spec.ts`；独立运行配置：`tests/e2e/playwright.ext_route_002.config.ts`。未改动未提交的 EXT-ROUTE-001 测试或其他角色文件。
- 接收角色：实现 Agent；仅修复插件实现与可加载 ZIP，保持旧 URL/hash、登录、输入错误行为。完成后以 `READY_FOR_TEST` 交回本测试角色独立复测；不得修改这些测试或断言。
- 未覆盖风险：未与真实后端联机保存本组场景；插件-平台 API 联机集成需在实现后的相邻端到端/产品验收中核对。

## 黑盒声明

未读取、搜索或分析 `frontend/src/`、`backend/apps/`、生产配置或插件 ZIP 内源码。测试依据任务单和公开 APP-009/APP-012 契约，所有生产行为结论来自扩展弹窗与 HTTP 请求观察。
