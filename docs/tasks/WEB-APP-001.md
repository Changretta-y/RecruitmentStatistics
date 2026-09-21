# WEB-APP-001 投递 API 类型与查询状态

- 状态：`DONE`
- 用户价值：前端对投递数据、时间和查询参数有稳定类型，避免页面之间混用字段格式。
- 范围：应用类型、API client、snake_case/camelCase 约定、查询状态和 URL query 序列化。
- 非范围：列表视觉页面、表单组件、后端 API 行为。
- 依赖：`WEB-AUTH-001`、`APP-004`、`APP-005`、`APP-006`、`APP-007`。
- 允许修改范围：测试 Agent：`frontend/tests/`、`docs/test-reports/`；实现 Agent：`frontend/src/`、`docs/implementation-notes/`；项目管理 Agent：仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`。

## 业务规则与公开契约

- `JobApplication` 类型包含 id、公司、岗位、状态、currentStage、六个 `string|null` 时间、备注和时间戳。
- 查询状态含 page、pageSize(10/20/50/100)、search、status、stage、时间范围和 ordering。
- 查询参数序列化与后端字段契约一致；空筛选不发送无意义值，排序保留 `-`。
- URL query 是查询状态的可恢复来源，解析非法值时回退默认值，不让页面崩溃。

## 验收标准

- [x] 类型覆盖成功响应、分页响应和统一错误字段。
- [x] 查询状态可在对象与 URL query 之间双向稳定转换。
- [x] 时间 null、ISO 字符串和字段命名转换无信息丢失。
- [x] API 方法正确传递认证、分页、筛选、排序和 PATCH null。
- [x] 工具和 API mock 测试先 RED 后独立复测。

## 风险与测试边界

- 具体组件行为由后续页面任务验证；此任务不要求渲染完整列表。
- 任何 API client 不得绕过统一 HTTP 层。
