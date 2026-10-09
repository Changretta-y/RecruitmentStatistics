# EXT-ROUTE-003 验收记录

- 状态：`DONE`
- 任务单：[`docs/tasks/EXT-ROUTE-003.md`](../tasks/EXT-ROUTE-003.md)
- RED 报告：[`docs/test-reports/EXT-ROUTE-003-red.md`](../test-reports/EXT-ROUTE-003-red.md)，提交 `4ebb285`
- 实现说明：[`docs/implementation-notes/EXT-ROUTE-003.md`](../implementation-notes/EXT-ROUTE-003.md)，提交 `9a0163d`
- TEST_PASSED：[`docs/test-reports/EXT-ROUTE-003-passed.md`](../test-reports/EXT-ROUTE-003-passed.md)，提交 `d41baca`
- 验收日期：2026-10-09

## 标准与证据

- [x] 插件登录后读取当前账号应用列表，按公司聚合展示公司名和岗位，不泄露其他用户数据。
- [x] 公司名和岗位名搜索、跨页去重、刷新、空结果、认证失败、网络重试均可观察。
- [x] 退出登录后列表与搜索清理，采集表单及 EXT-ROUTE-001/002 行为不回归。
- [x] Edge MV3 可加载 ZIP 专项与相邻回归合计 21/21 通过。

## 结论

- 结果：通过。
- 任务状态：`DONE`。
