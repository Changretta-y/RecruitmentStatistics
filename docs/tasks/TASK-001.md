# TASK-001：工程基线与健康检查接口

## 1. 任务元数据

- 任务编号：`TASK-001`
- 任务名称：工程基线与健康检查接口
- 所属阶段：工程基线（系统设计方案定义的首个实现阶段）
- 当前状态：`DONE`
- 指派角色：测试 Agent → 实现 Agent → 测试 Agent 独立复测 → 项目管理 Agent 验收
- 任务来源：`校招进度管理系统-详细设计方案.md` 首个阶段；当前仓库尚无任务单、测试目录或 `RED_CONFIRMED` 证据

## 2. 目标

建立可运行的项目最小基线，并提供供部署探针、测试和后续模块使用的健康检查公开接口。该任务只覆盖基线和健康检查，不提前实现招聘进度业务功能。

## 3. 公开契约

### 3.1 健康检查

- 请求：`GET /api/v1/health/`
- 认证：无需认证。
- 成功响应：HTTP `200`，响应体为 JSON，至少包含 `status` 字段且值为 `ok`。
- 成功响应示例：

  ```json
  {"status": "ok"}
  ```

- 响应头：声明 JSON 内容类型。
- 方法约束：对该路径不支持的方法必须返回框架约定的 4xx，不得误报为健康成功。
- 健康语义：接口只表示应用进程已启动并能处理请求；不得要求后续业务模块已实现，也不得把未纳入本任务的业务数据作为成功条件。

### 3.2 基线约束

- 后端服务能够按仓库约定启动。
- API 路径使用 `/api/v1/` 前缀，健康检查路径末尾保留 `/`。
- 不改变既有公开接口；若仓库尚无既有接口，则不得借本任务引入未在任务单中声明的业务接口。

## 4. 允许修改范围

实现 Agent 允许修改：

- `backend/apps/`
- `backend/config/`
- `backend/manage.py`
- `frontend/src/`
- `docs/implementation-notes/`
- 实现运行所需的依赖或生产配置（按 AGENTS.md 的内容归属规则）

测试 Agent 允许修改：

- `backend/tests/`
- `frontend/tests/`
- `tests/e2e/`
- `docs/test-reports/`

项目管理 Agent允许修改：

- `docs/requirements/`
- `docs/tasks/`
- `docs/acceptance/`

本任务中，任何角色均不得把测试放入 `backend/apps/*/tests/`。实现 Agent不得修改测试目录，测试 Agent不得修改生产实现目录。

## 5. 验收标准

验收必须在收到测试 Agent 的 `TEST_PASSED` 报告后进行；项目管理 Agent不得以实现 Agent 自测替代独立复测。

### 必须通过

1. `GET /api/v1/health/` 返回 HTTP `200`。
2. 响应可解析为 JSON，并包含 `status: "ok"`。
3. 响应声明 JSON 内容类型。
4. 健康检查不依赖尚未实现的招聘进度业务数据。
5. 至少一个不支持的方法不会返回健康成功响应。
6. 测试 Agent 已先提交失败原因确为缺失行为的 `RED_CONFIRMED` 证据，再由实现 Agent完成实现，最后由测试 Agent独立复测通过。
7. 任务单、RED 报告、实现说明和通过报告均可追溯到 `TASK-001`。

### 不在本任务范围

- 招聘批次、候选人、投递记录、面试或进度统计等业务模型和接口。
- 权限体系、登录、审计、通知、报表和部署平台集成。
- 用修改测试或放宽断言的方式获得通过。

## 6. TDD 状态流转

```text
PLANNED
  → TEST_WRITING
  → RED_CONFIRMED
  → IMPLEMENTING
  → READY_FOR_TEST
  → TEST_PASSED
  → ACCEPTING
  → DONE
```

测试 Agent 已提交 `RED_CONFIRMED`，实现 Agent 已完成生产实现，测试 Agent 已独立复测并提交 `TEST_PASSED`；项目管理 Agent 已完成验收，任务状态为 `DONE`。

## 7. 交付物清单

- [ ] `TASK-001` 任务单（本文件）
- [ ] 测试 Agent 的 RED 报告：`docs/test-reports/`
- [ ] 测试代码：`backend/tests/`、`frontend/tests/` 或 `tests/e2e/`（按实际测试层选择）
- [ ] 实现 Agent 的实现说明：`docs/implementation-notes/`
- [ ] 测试 Agent 的 `TEST_PASSED` 报告：`docs/test-reports/`
- [ ] 项目管理 Agent 的验收记录：`docs/acceptance/`



