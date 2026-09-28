# SHARE-001 互相授权投递记录 API 与默认头像

- 状态：PLANNED
- 用户价值：同意后双方只读查看投递记录，解除后恢复隔离。
- 依赖：AUTH-001～004、APP-003～008 已完成；需求 `docs/requirements/SHARE-001.md`。
- 范围：随机推荐与精确 ID 搜索、申请/通过/拒绝、共享列表/解除、只读分页、随机持久头像（新旧用户）、配置与数据库迁移。
- 非范围：页面、通知、原 CRUD 访问权限扩展、部署。
- 角色：根 Agent 为项目管理；share_tests 为测试；share_implementation 为实现，各 Agent 全程单一角色。
- 可写范围：测试仅 `backend/tests/`、`docs/test-reports/` 及必要测试配置；实现仅 `backend/apps/`、`backend/config/`、`backend/manage.py`、`docs/implementation-notes/` 及必要运行时配置；项目管理仅需求、任务、验收目录。

## 业务规则与公开契约

所有接口均位于 `/api/v1/sharing/`，要求 Bearer 认证。公共用户结构 `{id, username, avatar, relationship}`；avatar 为 `avatar-01`～`avatar-08` 中一个稳定值；relationship 为 `none|outgoing_pending|incoming_pending|connected`。公共用户信息不含邮箱等敏感字段。

1. `GET me/`：返回当前用户公共结构，用于显示我的 ID 和头像。
2. `GET users/recommendations/`：`{count, results:[公共用户]}`，按需求随机推荐；默认配置 10。非法配置必须在配置检查/启动阶段明确报错。有效配置范围 1～50。
3. `GET users/{user_id}/`：精确数字 ID 搜索；自身、不存在、停用为 `404 NOT_FOUND`；非正整数为 `400 VALIDATION_ERROR`。
4. `GET requests/`：`{incoming:[], outgoing:[]}`，包括历史与当前申请，最多各最近 100 条，按创建时间/id 倒序。每项 `{id, sender:公共用户, recipient:公共用户, status, created_at, responded_at}`；status 为 `pending|accepted|rejected|revoked`，待处理 responded_at 为 null。
5. `POST requests/`：body `{recipient_id:正整数}`，成功 `201` 返回申请项；不存在/停用目标 `404`；自身或非法输入 `400 VALIDATION_ERROR`；该用户对任一方向已有 pending/accepted 申请 `409 SHARING_CONFLICT`。并发不得生成两个有效申请。rejected/revoked 后可重新申请，不覆盖历史。
6. `POST requests/{request_id}/respond/`：`{decision:'accepted'|'rejected'}`；只有接收人可操作，陌生人或发送人 `404`；非 pending `409 SHARING_CONFLICT`，无效 decision `400`；成功 `200` 返回更新申请。accepted 原子地建立双向只读授权。
7. `GET connections/`：`{results:[{id, user:公共用户, created_at}]}`，id 为已接受申请 ID；双方均能列出对方，用户停用后不可见且不可读。
8. `DELETE connections/{connection_id}/`：任一当事人成功 `204`，申请转 revoked；无授权/不存在 `404`；撤销后双方下一次读请求立即 `404`。
9. `GET users/{user_id}/applications/`：仅已 connected 双方可读，其他情形（含本人）一律 `404`；用 APP-004 分页容器，默认 20/可选 10、20、50、100；非法分页 400，超页 200 空 results；支持 `search` 模糊搜索公司/岗位。稳定按 `-updated_at,-id` 排序。字段为既有投递输出去掉 notes 与 user 信息，包含 application_url 与六阶段 duration。任何非 GET 方法不得修改记录（405 或拒绝）。每次请求检查当前授权，不信任前端参数。

新旧用户均随机分配并持久保存头像；`me`、推荐、搜索、申请和共享用户中的同一人头像一致，刷新不变化；原注册/登录/me 响应无需扩大安全字段契约。必要迁移由实现产出，测试只能通过公开输入输出观察头像。

## 输入、输出与错误行为

错误沿用 `{code,message,details}`；未认证所有新接口 401。不接受客户端伪造 sender/owner/status 绕过权限。旧 CRUD 继续仅本人，授权也不能通过旧详情/PATCH/DELETE 访问对方。

## 验收标准

- [ ] 推荐默认最多 10、可配置、去重、排除自身/停用/已联系；数字 ID 搜索和公共字段符合契约。
- [ ] 新旧用户头像有效、稳定、多处一致，不扩大认证字段。
- [ ] 发申请、收到/发出历史、拒绝、显式通过、冲突处理及第三方隔离正确。
- [ ] 同意后双向只读分页/搜索正确，备注和敏感字段不可见，旧 CRUD 隔离不放宽。
- [ ] 解除后立即双向拒绝，再申请合法；停用用户也拒绝读取。
- [ ] RED、实现说明、独立通过报告、数据库迁移证据齐全。

## 风险与测试边界

测试不读取/搜索/枚举生产实现，只通过注册/登录/HTTP 及公开 Django User 测试夹具控制活跃性，配置通过 override_settings；推荐随机不要求每次必然不同。并发唯一性需实现提供数据库约束/事务说明并测试有效申请幂等边界。测试环境遵守 docs/agents/environment.md；保留已有无关未提交文件。先提交测试再生产，禁止推送（可能触发部署）。
