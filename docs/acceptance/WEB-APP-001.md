# WEB-APP-001 验收记录

- 状态：`DONE`
- 验收结论：`ACCEPTED`
- 验收角色：项目管理 Agent
- 验收日期：2026-09-21
- 任务单：`docs/tasks/WEB-APP-001.md`
- RED 报告：`docs/test-reports/WEB-APP-001-red.md`
- 测试通过报告：`docs/test-reports/WEB-APP-001-passed.md`
- 实现说明：`docs/implementation-notes/WEB-APP-001.md`
- 验收环境：Node.js `20.19.0`；npm `10.8.2`；Vitest `4.1.11`

## 系统设计契约对照

- `JobApplication` 与分页响应使用前端 camelCase 类型，API 边界负责与后端 snake_case 字段互转。
- 查询状态包含 page、pageSize、search、status、stage、时间范围和 ordering；默认第 1 页、每页 20 条、按 `-updated_at` 排序，pageSize 允许 10/20/50/100。
- 查询参数遵循 `/api/v1/applications/` 契约：空筛选不发送无意义值，搜索、状态/阶段和时间范围字段按后端名称传递，ordering 保留 `-` 前缀。
- URL query 是可恢复来源，非法值回退默认值；API 通过统一认证 HTTP 层调用，PATCH 的 null 必须保留。

## 标准与证据

- [x] 标准 1：类型覆盖成功响应、分页响应、统一错误字段以及 snake_case/camelCase 转换。独立专项测试验证分页结果、记录字段和错误类型/details。
- [x] 标准 2：查询状态可在对象与 URL query 之间稳定双向转换，pageSize 白名单和非法值回退符合契约。独立专项测试全部通过。
- [x] 标准 3：null、ISO 时间字符串和字段命名转换无信息丢失。独立测试覆盖响应、请求及时间字段的 null/ISO 保留。
- [x] 标准 4：API 方法通过统一 HTTP 层传递认证、分页、筛选、排序和 PATCH null；空筛选省略，ordering 的 `-` 保留。独立 API mock 测试覆盖这些公开调用行为。
- [x] 标准 5：工具和 API mock 测试先形成真实 RED，再由测试 Agent 独立复测。RED 报告记录 applications API/query 公开模块缺失导致 `12 failed`；实现说明状态为 `READY_FOR_TEST`；最终报告状态为 `TEST_PASSED`。

## 回归与质量门禁

- [x] 独立复测 4 个测试文件全部通过，共 `35 passed`，包含 WEB-AUTH-001、WEB-AUTH-002、WEB-AUTH-003 回归。
- [x] 通过报告确认 npm ci 成功、命令退出码为 0，测试期间未修改 `frontend/src`；Vue Router 空路径 warning 不影响断言或通过结果。
- [x] RED、实现说明、最终通过报告和本验收记录齐全；本次项目管理验收仅修改 `docs/acceptance/` 和 `docs/tasks/`。

## 结论

WEB-APP-001 的投递数据类型、分页响应转换、统一错误字段、查询状态 URL 同步、筛选/排序参数、时间/null 保留及统一认证 API 调用均满足任务单和系统设计契约。项目管理验收结论为 `ACCEPTED`，任务状态设置为 `DONE`。
