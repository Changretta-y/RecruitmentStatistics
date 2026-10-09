# EXT-ROUTE-005 验收记录

- 状态：`DONE`
- 任务单：[`docs/tasks/EXT-ROUTE-005.md`](../tasks/EXT-ROUTE-005.md)
- RED 报告：[`docs/test-reports/EXT-ROUTE-005-red.md`](../test-reports/EXT-ROUTE-005-red.md)，提交 `257fc8e`
- 实现说明：[`docs/implementation-notes/EXT-ROUTE-005.md`](../implementation-notes/EXT-ROUTE-005.md)，提交 `b5f3ff1`
- TEST_PASSED：[`docs/test-reports/EXT-ROUTE-005-passed.md`](../test-reports/EXT-ROUTE-005-passed.md)，提交 `5e160ec`
- 验收日期：2026-10-09

## 标准与证据

- [x] 登录后默认仅显示“查看投递记录”和“新增投递”两个入口。
- [x] 记录页与新增页互斥、按需显示，均可返回入口；退出清理并保留认证行为。
- [x] 记录搜索、采集保存、认证异常和版本回归通过；自动化合计 10/10。
- [x] 采用本地 CSS 实现主站一致的蓝色主按钮、白色卡片、圆角边框和焦点样式。

## 结论

- 结果：通过。
- 任务状态：`DONE`。
