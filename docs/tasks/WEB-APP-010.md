# WEB-APP-010 替换项目 Logo 资源

- 状态：`TEST_WRITING`
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
