# WEB-APP-009 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/public/logo.png`、`frontend/src/index.html`、`frontend/src/components/AppShell.vue`、`frontend/src/vite.config.ts`。
- 已实现行为：将用户提供的 PNG 原字节保存为 `/logo.png`；网页 `rel="icon"` 指向该资源，AppShell 侧栏品牌区以带 `alt="校招进度管理系统 Logo"` 的图片替换 briefcase 主图标，项目名称继续显示。图片按 36×36 等比容纳。
- 数据库迁移：无。
- 配置变化：Vite 以前设置 `publicDir: false`，现指向 `frontend/public`，使 `/logo.png` 在开发服务器和构建产物中保持同一路径；未增加依赖。
- 已知限制：使用原图而未重绘或修改，极小尺寸的浏览器标签页显示效果取决于浏览器缩放。
- 自检结果：附件、`frontend/public/logo.png` 与 `frontend/dist/logo.png` 的 SHA-256 均为 `9C0420FD9643705BD36A1C9E8E5C4D80B5FE100EA5B22492BB1301ABBA610403`；WEB-APP-009 Edge 公开专项 3/3 通过；`npm run lint` 和 `npm run build` 通过；构建 HTML 的 favicon 路径为 `/logo.png`。
- 建议复测命令：`npm run test:sharing -- --config=tests/playwright.web_app_009.config.mts --reporter=line`；`npm run lint`；`npm run build`。
- 测试完整性声明：未修改测试、断言或质量门槛；WEB-APP-008 工作区未提交改动原样保留。
