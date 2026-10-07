# WEB-APP-009 项目 Logo 与网页图标

- 状态：`DONE`
- 角色：项目管理=主 Agent；独立测试=release_tests；独立实现=company_implementation。
- 用户价值：项目在浏览器标签页、侧栏和内部品牌区域使用统一的项目 Logo，形成一致识别。
- 资源来源：用户本次附件 `codex-clipboard-4ff5e87c-fa2d-4382-83b7-c83163af7ef5.png`；SHA-256 `9C0420FD9643705BD36A1C9E8E5C4D80B5FE100EA5B22492BB1301ABBA610403`。实现角色可从 `C:\Users\Yinchengyu\AppData\Local\Temp\codex-clipboard-4ff5e87c-fa2d-4382-83b7-c83163af7ef5.png` 读取后复制到项目资源目录。
- 范围：Logo 静态资源、网页 favicon、AppShell 品牌区域和前端构建产物。
- 非范围：重新绘制图片、后端接口、手机端专门适配、浏览器扩展品牌重构。
- 允许修改范围：项目管理仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`；测试仅 `frontend/tests/`、`docs/test-reports/`；实现仅 `frontend/src/`、`frontend/public/`、`frontend/index.html`（如存在）和 `docs/implementation-notes/`。

## UI 契约

- 用户提供的图片保存为项目 Logo 静态资源，前端构建后可通过公开 URL 加载。
- `frontend/index.html` 的 favicon 指向该 Logo 资源；浏览器标签页不再使用缺省图标。
- AppShell 侧栏品牌区域显示该 Logo 图片，并提供可访问的替代文本/名称；项目名称继续显示。
- 内部主品牌标识使用 Logo 图片，不以单独的 briefcase 图标代替；导航功能图标可以继续保留。
- Logo 资源在开发服务器和生产构建产物中均可访问；不新增运行时依赖。

## 验收标准

- [ ] Logo 资源存在、格式可被浏览器加载，构建后路径稳定。
- [ ] favicon 链接存在并指向 Logo 资源。
- [ ] AppShell 品牌区显示 Logo 和项目名称，Logo 有可访问替代文本。
- [ ] 现有登录、导航、列表和构建回归不受影响。

## Agent 交接

- 测试角色先通过公开文件、DOM 和构建行为确认 RED，再交实现角色。
- 实现角色不得修改测试；测试角色不得读取生产实现目录。
- 不覆盖工作区中与本任务无关的 WEB-APP-008 未提交改动。

## 2026-10-07 RED 与实现交接

- 测试先行提交：`974817c`；报告：`docs/test-reports/WEB-APP-009-red.md`。
- Edge 桌面套件连续两次为 1/3 通过、0 flaky；登录和项目标题基线通过，favicon 有效链接与侧栏 Logo 图片两项稳定缺失。
- 测试使用用户附件 SHA-256 校验未来 favicon 与侧栏 Logo 的实际响应字节，避免替换为其他图片。
- 状态轨迹：TEST_WRITING → RED_CONFIRMED → IMPLEMENTING。
- 接收实现角色：company_implementation；可写 `frontend/src/`、`frontend/public/`、`frontend/src/index.html` 和 `docs/implementation-notes/WEB-APP-009.md`，测试目录只读；保留 WEB-APP-008 未提交改动。

## 2026-10-07 实现交接

- 实现提交：`634339e`；说明：`docs/implementation-notes/WEB-APP-009.md`。
- 已实现：用户原图复制为 `frontend/public/logo.png`；`src/index.html` favicon 指向 `/logo.png`；AppShell 侧栏品牌使用带 alt 的图片；Vite `publicDir` 指向前端静态资源目录。
- 自检：附件、public、dist 三处 SHA-256 一致；Logo Edge 专项 3/3、lint/build、staged diff check 通过。
- 接收测试角色：release_tests；独立复测 Logo 字节、favicon、侧栏可访问图片和相邻登录/导航回归后提交 TEST_PASSED。

## 2026-10-07 PM 验收结果

- 状态：DONE。
- 独立报告：`docs/test-reports/WEB-APP-009-passed.md`，提交 `d23505d`；实现提交 `634339e`；有效 RED `974817c`。
- [x] 用户原图以 `frontend/public/logo.png` 保存，开发服务器和构建产物字节均匹配附件 SHA-256。
- [x] `src/index.html` 与构建 HTML 的 favicon 均指向 `/logo.png`。
- [x] AppShell 侧栏品牌区显示 Logo 图片和可访问替代文本，项目名称、登录和导航保持正常。
- [x] Edge 专项 4/4、lint/build 通过；WEB-APP-008 未提交改动保持不变。
- 结论：任务契约全部满足，项目管理 Agent 设置 DONE。
