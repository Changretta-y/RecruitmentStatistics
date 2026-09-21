# TDD 工作流

触发：任务交接、状态变更、失败回流、复测和验收路由。

## 状态机

| 状态 | 设置角色 | 完成条件 |
|---|---|---|
| `PLANNED` | 项目管理 | 任务单和验收标准完整 |
| `TEST_WRITING` | 测试 | 正在把契约转成测试 |
| `RED_CONFIRMED` | 测试 | 测试因缺失行为稳定失败 |
| `IMPLEMENTING` | 实现 | 正在编写或修复生产实现 |
| `READY_FOR_TEST` | 实现 | 实现说明完整，等待独立复测 |
| `TEST_FAILED` | 测试 | 失败报告可复现，已退回实现 |
| `TEST_PASSED` | 测试 | 任务测试与必要回归全部通过 |
| `ACCEPTING` | 项目管理 | 正在逐条黑盒验收 |
| `ACCEPTANCE_FAILED` | 项目管理 | 验收证据表明仍需返工 |
| `DONE` | 项目管理 | 测试通过且验收通过，交付物齐全 |
| `BLOCKED` | 当前角色 | 阻塞原因、所需决策和责任人明确 |

主路径：

```text
PLANNED → TEST_WRITING → RED_CONFIRMED → IMPLEMENTING
→ READY_FOR_TEST → TEST_PASSED → ACCEPTING → DONE
```

回流路径：

```text
READY_FOR_TEST → TEST_FAILED → IMPLEMENTING
ACCEPTING → ACCEPTANCE_FAILED → IMPLEMENTING       # 行为错误
ACCEPTING → ACCEPTANCE_FAILED → TEST_WRITING       # 覆盖缺口或契约修订
```

每次实现修复后都回到 `READY_FOR_TEST`，由测试 Agent复测；不存在从实现或验收直接到 `TEST_PASSED` 的路径。

## 交接步骤

1. 发送方记录任务编号、当前状态、已完成内容和产物路径。
2. 写明接收角色的工作范围、输入文档、建议命令、已知风险和完成条件。
3. 接收方确认角色边界和允许修改目录后开始工作。
4. 状态只能由表中指定角色设置。

完成标准：接收方能仅凭交接和指向的材料开始本阶段，并能明确判定何时完成。

## Git 证据

- 测试提交先于实现提交，保留 RED 证据。
- 测试与实现分开提交。
- 推荐提交顺序：`test(任务编号)` → `feat(任务编号)` → 必要的 `fix(任务编号)` → 结果文档。
- 各角色保留其他角色的未提交改动；发现重叠修改先交由项目管理 Agent 排序。

