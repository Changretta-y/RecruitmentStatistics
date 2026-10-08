# EXT-ROUTE-002 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/src/browser-extension/core.js` 的岗位匹配逻辑、`frontend/src/browser-extension/service-worker.js` 的目标岗位更新路由、生成的 `artifacts/recruitment-capture-extension-v0.1.0.zip`。
- 已实现行为：已完整填写公司名与岗位名时，逐个检查公司聚合下的岗位，以去空白、折叠连续空白及大小写归一化后的公司名和岗位名作为身份。没有同名岗位时生成新建预览并以 flat `POST /api/v1/applications/` 追加，招聘入口 URL 即使与旧岗位相同也不会抢先命中旧记录。
- 已实现行为：唯一同名岗位可更新，PATCH 路径始终使用公司聚合 ID；聚合内第二个及以后岗位的受支持字段使用带岗位 ID 的 nested PATCH，避免改到首岗位。多个同名岗位保留独立岗位 ID 供用户显式选择，也可明确新建；未选择时禁止写入。缺失公司名或岗位名会明确报错。
- 数据库迁移：无。
- 配置变化：无。交付 ZIP 用 `npm run build:extension` 从插件源生成。生成包保留工作区先前 EXT-ROUTE-001 的 URL/hash 修复；该修复不属于本任务新匹配代码，本次源码提交不会额外暂存其原有 hunk。项目管理 Agent 需保证 EXT-ROUTE-001 源码变更随后单独纳入版本历史，维持重新打包一致性。
- 已知限制：当前 APP-012 后端的 nested 岗位写入不接收 `application_url`，flat PATCH 也会丢弃该字段。因此非首岗位若单独改链接，插件明确提示平台暂不支持，不会误报更新成功或误改首岗位；后端补齐岗位 URL 写入契约需另行任务。现有首岗位 flat PATCH 请求及其公开请求体保持兼容。
- 自检结果：Node 20.19.0、npm 10.8.2 下 `npm run build:extension` 成功；从可加载 ZIP 运行 EXT-ROUTE-002 黑盒 7/7、EXT-ROUTE-001 URL/hash 回归 7/7；`node --check` 对 core 和 service worker 均通过。
- 建议复测命令：仓库根目录执行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_002.config.ts`，再运行 `npm exec -- playwright test --config=tests/e2e/playwright.ext_route_001.config.ts`；检查 ZIP 内六个插件文件可加载。
- 测试完整性声明：未修改测试、断言或质量门槛；其他角色工作区文件未回退。
