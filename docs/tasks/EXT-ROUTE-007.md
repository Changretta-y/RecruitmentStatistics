# EXT-ROUTE-007 插件使用平台 Logo 图标

- 状态：RED_CONFIRMED
- 用户价值：浏览器工具栏和扩展管理页能直接识别平台品牌，不再使用默认拼图图标。
- 范围：将平台 `frontend/public/logo.png` 作为扩展图标加入插件包，更新 Manifest 的扩展图标和 action 图标配置，保持版本号 `0.2.0`。
- 非范围：不改变插件弹窗布局、采集、记录搜索、认证和保存逻辑；不重绘或压缩平台 Logo。
- 依赖：EXT-ROUTE-006 插件 v0.2.0 包；平台 Logo 资源。
- 允许修改范围：项目管理仅 `docs/tasks/`、`docs/acceptance/`；测试仅 `tests/e2e/`、`docs/test-reports/`；实现仅 `frontend/src/browser-extension/`、`scripts/build-extension.mjs`、生成 `artifacts/`、`docs/implementation-notes/`。

## 公开契约

1. Manifest 的 `icons` 和 `action.default_icon` 指向插件包内的平台 Logo 文件。
2. 插件包中的 Logo 字节与 `frontend/public/logo.png` 完全一致，不裁剪、不压缩、不替换。
3. 插件包可加载，既有入口、记录、新增、认证和保存回归不变。

## 验收标准

- [ ] Manifest 声明扩展图标和 action 工具栏图标。
- [ ] ZIP 包含 Logo 文件且 SHA-256 与平台 Logo 一致。
- [ ] v0.2.0 可加载，既有插件专项回归通过。
- [ ] 测试 Agent 先 RED，实现 Agent READY_FOR_TEST，测试 Agent TEST_PASSED，PM 验收 DONE。

## Agent 交接

- 当前状态：PLANNED → TEST_WRITING。
- 测试 Agent：`company_tests`，仅修改 tests/e2e/ 与报告。
- 实现 Agent：`company_implementation`，仅修改插件图标、构建产物与说明。
