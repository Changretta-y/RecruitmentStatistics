# WEB-APP-010 替换项目 Logo 资源

- 状态：`READY_FOR_TEST`
- 角色：项目管理=主 Agent；独立测试=release_tests；独立实现=company_implementation。
- 用户价值：将项目当前品牌图片替换为用户最新提供的 Logo，网页和内部品牌区域保持统一。
- 资源来源：用户附件 `codex-clipboard-92ab7fb8-e5c5-4b5e-b6c6-ed4781e981d8.png`；SHA-256 `A09C7876116515619AC4A2ED0293ADE91077627A446329458CED6B9515D79E88`。实现角色可从 `C:\Users\Yinchengyu\AppData\Local\Temp\codex-clipboard-92ab7fb8-e5c5-4b5e-b6c6-ed4781e981d8.png` 读取。
- 范围：替换现有 `frontend/public/logo.png` 的原图字节，保留 favicon、AppShell 品牌区域和访问路径。
- 非范围：品牌布局、后端接口、Logo 重绘、手机端适配和其他 WEB-APP-008 功能。
- 允许修改范围：项目管理仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`；测试仅 `frontend/tests/`、`docs/test-reports/`；实现仅 `frontend/public/`、`docs/implementation-notes/`。

## 公开契约

- `/logo.png` 仍是 favicon 和 AppShell 品牌图片的唯一资源路径。
- 开发服务器、构建产物和线上静态资源的 Logo 字节必须与新附件 SHA-256 一致。
- AppShell 的 alt、项目名称、favicon 链接和现有导航行为保持正常。
- 不得把新图压缩、裁剪或替换成其他图片；允许构建工具复制但不改变字节。

## 验收标准

- [ ] 新资源 SHA-256 与用户附件一致。
- [ ] favicon 和侧栏品牌图片仍可加载并使用新资源。
- [ ] 登录、导航、构建回归通过。

## Agent 交接

- 测试先依据当前旧资源确认稳定 RED，再交实现角色。
- 实现角色只替换资源并写实现说明，不修改测试或无关 WEB-APP-008 改动。

## 2026-10-07 RED 与实现交接

- 测试先行提交：`17083c6`；报告：`docs/test-reports/WEB-APP-010-red.md`。
- Edge 连续两次为 1/3 通过、0 flaky；登录/导航基线通过，本地 favicon 与侧栏 `/logo.png` 均稳定返回旧 Logo SHA，不匹配新附件 SHA。
- 状态轨迹：TEST_WRITING → RED_CONFIRMED → IMPLEMENTING。
- 接收实现角色：company_implementation；只替换 `frontend/public/logo.png` 原始字节并写实现说明，保留 favicon 路径、AppShell 结构、既有 APP-010 测试和 WEB-APP-008 未提交改动。

## 2026-10-07 实现交接

- 实现提交：`15b1f2e`；说明：`docs/implementation-notes/WEB-APP-010.md`。
- 用户附件、`frontend/public/logo.png` 和构建产物 `dist/logo.png` SHA-256 均为 `A09C7876116515619AC4A2ED0293ADE91077627A446329458CED6B9515D79E88`。
- Logo Edge 专项 3/3、lint/build、staged diff check 通过；favicon/AppShell 路径和结构未修改。
- 接收测试角色：release_tests，独立复测新 Logo 字节、favicon、侧栏与导航回归后提交 TEST_PASSED。
