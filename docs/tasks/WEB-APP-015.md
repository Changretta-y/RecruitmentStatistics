# WEB-APP-015 提示词复制兼容与卡片折叠

- 状态：DONE
- 用户价值：在 HTTP/权限受限环境中也能可靠复制提示词，长提示词不会撑满列表。
- 范围：修复提示词复制兼容回退和失败提示；卡片正文固定长度预览，点击卡片查看完整内容。
- 非范围：不改变提示词 API、数据隔离、搜索、新增、编辑、删除和预设内容。
- 依赖：WEB-APP-014 `/prompts` 页面。
- 允许修改范围：项目管理仅 `docs/tasks/`、`docs/acceptance/`；测试仅 `frontend/tests/`、`docs/test-reports/`；实现仅 `frontend/src/`、`docs/implementation-notes/`。

## 公开 UI 契约

- 点击“复制”应复制完整提示词内容；优先使用 `navigator.clipboard.writeText`，不可用或拒绝时使用页面内兼容回退，成功显示“复制成功”。
- 当现代 API 和兼容回退都失败时，显示明确失败提示，不能误报成功，提示词记录仍保留。
- 列表卡片正文只显示固定长度预览（不超过 160 个字符，超出显示省略号）；完整内容不在卡片中展开。
- 点击卡片或“查看详情”可打开详情对话框，显示完整标题和内容；详情关闭后回到列表。
- 现有编辑、删除、搜索和新增操作继续可用。

## 验收标准

- [ ] HTTP/剪贴板不可用时复制回退成功并提示成功。
- [ ] 双重复制失败时提示失败，记录未被修改。
- [ ] 长内容卡片预览固定长度，详情能查看完整内容。
- [ ] WEB-APP-014 核心回归通过。

## RED 证据

- 测试提交：`b52a8df`
- 报告：`docs/test-reports/WEB-APP-015-red.md`
- 结果：专项 1 passed / 4 failed / 0 errors；失败均为复制回退、固定预览和详情行为缺失，WEB-APP-014 核心回归 8/8。

## Agent 交接

- 当前状态：READY_FOR_TEST → TEST_PASSED → ACCEPTING → DONE。
- 实现 Agent：`release_implementation`，只改 `frontend/src/` 和实现说明。

## 实现交接

- 实现提交：`dc795e9`
- 实现说明：`docs/implementation-notes/WEB-APP-015.md`
- 实现自测：WEB-APP-015 Playwright 5/5。

## TEST_PASSED 证据

- 测试更新：`1e2fcf5`
- 通过报告：`docs/test-reports/WEB-APP-015-passed.md`
- 结果：015 专项 5/5，WEB-APP-014 回归 8/8。
