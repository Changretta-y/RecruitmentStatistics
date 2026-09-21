# WEB-APP-003 验收记录

- 状态：`DONE`
- 验收结论：`ACCEPTED`
- 验收角色：项目管理 Agent
- 验收日期：2026-09-21
- 任务单：`docs/tasks/WEB-APP-003.md`
- RED 报告：`docs/test-reports/WEB-APP-003-red.md`
- 测试通过报告：`docs/test-reports/WEB-APP-003-passed.md`
- 实现说明：`docs/implementation-notes/WEB-APP-003.md`
- 验收环境：Node.js `20.19.0`；npm `10.8.2`；Vitest `4.1.11`

## 系统设计契约对照

- 共用 `ApplicationForm.vue` 支持新增和编辑；新增默认状态为 `applied`，公司/岗位和备注为空，六个阶段时间均为空。
- 时间字段支持选择和键盘输入，提交前使用 ISO 8601；未填写或清空明确发送 JSON `null`。
- 编辑使用传入记录的副本，PATCH 仅提交变化字段；成功后关闭、清理表单并刷新第 1 页，失败保留输入并显示字段错误。
- 提交期间按钮禁用并显示 loading，关闭脏表单前二次确认；前端不直接操作 localStorage。

## 标准与证据

- [x] 标准 1：新增、编辑两种模式字段回填和默认值正确。独立组件测试覆盖新增默认字段、完整字段展示、编辑回填以及原始列表行不被修改。
- [x] 标准 2：六阶段时间可设置、修改、清空，ISO/null 传输正确。独立测试覆盖六阶段输入、带时区 ISO 保留和清空为 `null`。
- [x] 标准 3：重复提交被阻止，成功和失败后的表单/列表状态符合契约。独立测试覆盖 loading、按钮禁用、重复提交阻止、成功关闭/清理/刷新第 1 页及失败保留输入。
- [x] 标准 4：后端字段错误映射到对应字段，成功前不乐观修改原始行。独立测试覆盖 snake_case 字段错误映射、编辑副本隔离和 PATCH 仅提交变化字段。
- [x] 标准 5：组件测试先形成真实 RED，再由测试 Agent 独立复测。RED 报告记录公开 `ApplicationForm.vue` 缺失导致测试无法收集；实现说明状态为 `READY_FOR_TEST`；最终报告状态为 `TEST_PASSED`。

## 回归与质量门禁

- [x] 独立复测 6 个测试文件全部通过，共 `51 passed`，包含 WEB-APP-001/002 及 WEB-AUTH-001/002/003 前端回归。
- [x] 通过报告确认 npm ci 成功、命令退出码为 0，测试期间未修改 `frontend/src`；既有 Vue Router warning 不影响断言或通过结果。
- [x] RED、实现说明、最终通过报告和本验收记录齐全；本次项目管理验收仅修改 `docs/acceptance/` 和 `docs/tasks/`。

## 结论

WEB-APP-003 的新增/编辑表单、字段默认与回填、阶段时间 ISO/null 处理、校验、重复提交保护、POST/PATCH 语义、成功/失败状态、字段错误映射、原始行隔离和未保存确认均满足任务单及系统设计契约。项目管理验收结论为 `ACCEPTED`，任务状态设置为 `DONE`。
