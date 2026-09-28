# WEB-SHARE-002 实现说明

- 状态：READY_FOR_TEST
- 实现角色：share_implementation；RED报告：`docs/test-reports/WEB-SHARE-002-red.md`；测试先行提交：`850870d`。
- 修改范围：`frontend/src/components/SharingUserRow.vue`及本说明。
- 已实现行为：共用用户行申请按钮从“申请互看”改为“申请共享”，同时覆盖推荐用户及ID搜索结果；事件、权限状态和重复提交禁用行为保持原逻辑。
- 数据库迁移/配置/依赖：无变化。
- 自检结果：精确单行标签diff；按PM交接无需额外自测，由原前端测试Agent独立复测现有专项及真实申请流程。
- 建议复测：`npm run test:sharing`，必要真实双用户流程；无需后端/全量测试。
- 测试完整性声明：测试只读，未新增测试或改变断言/门槛，未推送或部署。
