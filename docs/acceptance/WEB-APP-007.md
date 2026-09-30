# WEB-APP-007 验收记录

- 状态：DONE
- 任务单：[WEB-APP-007](../tasks/WEB-APP-007.md)
- 独立报告：[WEB-APP-007-passed.md](../test-reports/WEB-APP-007-passed.md)，提交 `09b91c0`
- 实现说明：[WEB-APP-007 实现说明](../implementation-notes/WEB-APP-007.md)，实现提交 `7d4f37b`

## 验收结论

- [x] 桌面端每个岗位为独立横向行，旧的岗位纵向大卡片已移除出主列表布局。
- [x] 单岗位默认直接显示；多岗位默认只显示首岗位，展开后追加其余岗位行。
- [x] 公司共享流程、更新时间、公司级编辑/删除操作只在首行显示，不随岗位重复。
- [x] 展开支持键盘和 `aria-expanded`/`aria-controls`，不会发起写请求，分页状态保持。
- [x] 相邻列表、编辑、删除、共享流程和构建回归均通过；桌面默认/展开截图可读。

结论：WEB-APP-007 全部验收标准通过，设置为 DONE。
