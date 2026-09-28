# WEB-SHARE-002 申请按钮文案调整

- 状态：DONE
- 用户价值：共享申请入口统一称为“申请共享”。
- 依赖：WEB-SHARE-001 已完成。
- 范围：推荐及ID搜索结果的申请按钮从“申请互看”改为“申请共享”；同步现有测试的公开按钮名称与现行契约。
- 非范围：授权流程、API、布局、部署；不新增镜像测试。
- 角色：根Agent项目管理；frontend_share_tests测试；share_implementation实现。
- 可写范围：PM仅docs/requirements、docs/tasks、docs/acceptance；测试仅frontend/tests、tests/e2e、docs/test-reports；实现仅frontend/src、docs/implementation-notes。

## 公开契约与验收标准

- [x] 推荐用户及ID搜索结果的发送申请按钮显示“申请共享”，不再显示旧文案。
- [x] 发送申请、禁重复与待同意状态保持原行为；现有共享专项通过。
- [x] 现有测试更新公开文案后先证明RED，再改生产并由原测试Agent独立复测；所有权保持，交付物齐全。

## 交接

测试Agent仅更新现有按钮名称断言/选择器，不新增测试；使用原有代表用例确认旧文案导致RED，随后交原实现Agent改生产标签。实现完成后原测试Agent独立运行共享专项与必要真实申请流程。禁止push，保留无关修改。

- RED报告：`docs/test-reports/WEB-SHARE-002-red.md`；测试先行提交`850870d`，三个已有代表用例因缺新按钮名称失败，环境正常；无新增测试。
- 实现提交`122ce97`，共享用户行单行标签与实现说明；交原测试Agent独立复测。
- 独立通过报告`docs/test-reports/WEB-SHARE-002-passed.md`，提交`dc66cd5`，现有共享17项及真实双用户1项合计18/0通过。
