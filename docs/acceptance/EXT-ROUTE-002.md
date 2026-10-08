# EXT-ROUTE-002 验收记录

- 状态：`DONE`
- 任务单：[`docs/tasks/EXT-ROUTE-002.md`](../tasks/EXT-ROUTE-002.md)
- RED 报告：[`docs/test-reports/EXT-ROUTE-002-red.md`](../test-reports/EXT-ROUTE-002-red.md)，提交 `13ad904`
- 实现说明：[`docs/implementation-notes/EXT-ROUTE-002.md`](../implementation-notes/EXT-ROUTE-002.md)，提交 `660787d`
- TEST_PASSED：[`docs/test-reports/EXT-ROUTE-002-passed.md`](../test-reports/EXT-ROUTE-002-passed.md)，提交 `61f0e57`
- 验收日期：2026-10-08

## 标准与证据

- [x] 同一公司不同岗位即使使用相同招聘 URL，也发送 POST 追加岗位，不再 PATCH 覆盖旧岗位。
- [x] 同公司同岗位仍按岗位身份更新；存在同名多岗位时显示选择/新建提示，不随机覆盖。
- [x] 新专项 7/7、EXT-ROUTE-001 URL/hash 回归 7/7 通过，登录、空输入和错误写入回归通过。
- [x] 交付 ZIP 可加载且包含修复；测试 Agent 未读取生产源码，生产实现未修改测试。

## 结论

- 结果：通过。
- 任务状态：`DONE`。
- 已知后续风险：APP-012 对非首岗位 `application_url` 的后端兼容写入限制已记录在实现说明中，另行建后端任务；不影响本任务防止跨岗位覆盖的验收结论。
