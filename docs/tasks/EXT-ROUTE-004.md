# EXT-ROUTE-004 升级浏览器插件版本号

- 状态：DONE
- 用户价值：浏览器能够识别插件功能更新，用户重新加载/更新时不会继续看到旧的 `0.1.0` 版本。
- 范围：将插件 manifest、构建产物文件名和使用说明统一升级到 `0.2.0`，重新生成可加载 ZIP。
- 非范围：不改变插件业务逻辑、权限、API、采集和保存行为。
- 允许修改范围：项目管理仅 `docs/tasks/`、`docs/acceptance/`；测试仅 `tests/e2e/`、`docs/test-reports/`；实现仅 `frontend/src/browser-extension/manifest.json`、`frontend/src/browser-extension/README.md`、`scripts/build-extension.mjs`、生成的 `artifacts/`、`docs/implementation-notes/`。

## 公开契约

- manifest `version` 为 `0.2.0`。
- 构建入口生成 `artifacts/recruitment-capture-extension-v0.2.0.zip`，包内 manifest 版本同为 `0.2.0`。
- 旧业务行为与现有插件回归不变。

## 验收标准

- [ ] 源码 manifest、构建脚本、README 和 ZIP 文件名统一为 `0.2.0`。
- [ ] 可加载 ZIP 包内版本为 `0.2.0`，且既有插件专项回归通过。
- [ ] 测试 Agent 先 RED，实现 Agent READY_FOR_TEST，测试 Agent TEST_PASSED，PM 验收 DONE。

## Agent 交接

- 当前状态：PLANNED → TEST_WRITING → RED_CONFIRMED → IMPLEMENTING。
- 测试 Agent：`company_tests`；仅修改黑盒测试与报告。
- RED 证据：测试提交 `7af46e4`，报告 `docs/test-reports/EXT-ROUTE-004-red.md`；ZIP 文件名和包内 manifest 版本均为旧 `0.1.0`，登录采集回归通过。
- 实现交接：提交 `361fb68`，说明 `docs/implementation-notes/EXT-ROUTE-004.md`；manifest/README/构建脚本统一 `0.2.0`，新 ZIP SHA `C67185D84D3692472533FFDC2DB8D3BB4574D969616E6D061B13B4C09F915D91`，Node check、确定性构建和专项 3/3 通过，交回测试 Agent。

## 2026-10-09 PM 验收结果

- 状态：DONE。
- RED 报告：`docs/test-reports/EXT-ROUTE-004-red.md`，提交 `7af46e4`。
- 实现说明：`docs/implementation-notes/EXT-ROUTE-004.md`，提交 `361fb68`。
- 独立通过报告：`docs/test-reports/EXT-ROUTE-004-passed.md`，提交 `19a7143`。
- [x] 新 ZIP 文件名、manifest 和 README 均升级到 `0.2.0`。
- [x] 新包可加载，登录/采集回归通过；新旧包除版本号外运行文件一致。

结论：插件版本升级契约全部满足，项目管理 Agent 设置 EXT-ROUTE-004 为 DONE。
