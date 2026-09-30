# WEB-APP-007 实现说明

- 状态：READY_FOR_TEST
- 修改范围：`frontend/src/views/ApplicationsView.vue`。
- 已实现行为：桌面公司列表改为按岗位逐行显示的横向表格。公司首行始终直接展示首岗位的名称、投递信息、岗位面试摘要和进度；多岗位时可用带 `aria-expanded`/`aria-controls` 的按钮展开或折叠，其余岗位展开后各占独立 `tr`。子行公司、共享流程、更新时间和公司级操作单元格留空；AI 面、测评、笔试只在首行显示一次。
- 已实现行为：岗位行保留投递链接、备注、面试名称与日期；公司级编辑、删除和确认流程保留。列宽按桌面表格分配，岗位行保持紧凑。展开状态只在前端切换，不改查询 URL、分页，也不发送写请求。
- 数据库迁移：无。
- 配置变化：无。
- 已知限制：本任务只以桌面端布局为验收目标；既有窄屏样式保留但未增加手机端专项适配。
- 自检结果：Node 20.19.0 下 WEB-APP-007 Edge 黑盒 5/5，通过；WEB-APP-006 非真实后端 Edge 相邻回归 11/11，通过；WEB-APP-002/004 Vitest 单 worker 15/15，通过；`npm run lint`、`npm run build` 与 `git diff --check` 通过。首次与浏览器套件并行执行的 Vitest 曾因运行负载出现 5 秒超时，随后单 worker 独立复跑全部通过。
- 建议复测命令：`npm run test:sharing -- --config=tests/playwright.web_app_007.config.mts --reporter=line`；`npm run test:sharing -- --config=tests/playwright.web_app_006.config.mts --grep-invert "real isolated" --reporter=line`；`npm run test -- tests/test_web_app_002.spec.ts tests/test_web_app_004.spec.ts --maxWorkers=1`；`npm run lint`；`npm run build`。
- 测试完整性声明：未修改测试、断言或质量门槛。
