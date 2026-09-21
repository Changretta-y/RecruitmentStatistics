# Agent 协作入口

本项目采用角色隔离的 TDD 流程：项目管理 Agent 拆解与验收，测试 Agent 先写测试并独立复测，功能实现 Agent 只写实现。一个 Agent 在一个任务中只承担一个角色。

## 开始任务

1. 确认任务编号和被指派的角色；角色未明确时停止工作，请项目管理 Agent 分派。
2. 阅读 [系统设计](校招进度管理系统-详细设计方案.md) 中与当前任务有关的需求和公开契约。
3. **环境**：当任务涉及安装依赖、切换运行时、执行脚本、测试或构建时，先读取 [uv 与 nvm 环境规范](docs/agents/environment.md)。
4. 按角色读取且只读取对应说明：
   - **项目管理**：当任务涉及需求拆解、调度或验收时，读取 [项目管理 Agent](docs/agents/project-manager.md)。
   - **测试编写**：当任务涉及测试设计、RED 证明、复测或测试报告时，读取 [测试 Agent](docs/agents/test-agent.md)。
   - **功能实现**：当任务涉及前后端实现、迁移或实现修复时，读取 [实现 Agent](docs/agents/implementation-agent.md)。
5. 当任务发生交接、失败回流或状态变更时，读取 [TDD 工作流](docs/agents/workflow.md)。
6. 当需要产出任务单、测试报告、实现说明或验收记录时，读取 [交付模板](docs/agents/templates.md)。

完成标准：已明确角色、输入文档、允许修改的目录、当前状态及本阶段完成条件。

## 所有权

| 角色 | 可写范围 | 交付物 |
|---|---|---|
| 项目管理 Agent | `docs/requirements/`、`docs/tasks/`、`docs/acceptance/` | 任务单、验收记录 |
| 测试 Agent | `backend/tests/`、`frontend/tests/`、`tests/e2e/`、`docs/test-reports/` | 失败测试、RED/复测报告 |
| 功能实现 Agent | `backend/apps/`、`backend/config/`、`backend/manage.py`、`frontend/src/`、`docs/implementation-notes/` | 生产实现、迁移、实现说明 |

共享配置按内容归属：测试 Agent 只改测试依赖与测试运行配置；实现 Agent 只改运行时依赖与生产配置。两者需要修改同一文件时，由项目管理 Agent 排定先后，双方分别提交自己的改动。

后端测试集中放在 `backend/tests/`，不在 `backend/apps/*/tests/` 中放测试，以保持实现与测试的目录隔离。

## 不可跨越的门禁

- **角色隔离**：项目管理 Agent 产出契约和验收结论；测试 Agent 产出测试证据；实现 Agent 产出生产代码。任何角色都不代替另一角色交付。
- **黑盒测试**：测试 Agent 依据需求、任务单和公开接口测试，只观察公开输入输出；生产实现目录对测试 Agent 是禁区。
- **测试完整性**：实现 Agent 将测试目录视为只读，以修复生产实现来满足测试。
- **RED 门禁**：新增实现从 `RED_CONFIRMED` 开始；失败必须由缺失行为导致，而非语法、夹具或环境错误。
- **独立复测**：实现 Agent 的自测不能代替测试 Agent 的复测。
- **验收门禁**：项目管理 Agent 只在收到 `TEST_PASSED` 报告后验收。
- **完成门禁**：只有项目管理 Agent 能设置 `DONE`，且任务单、RED 证据、实现说明、通过报告和验收记录必须齐全。

## 主流程

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

复测失败进入 `TEST_FAILED` 并回到原实现 Agent；验收发现行为错误也回到实现 Agent，修复后仍须由测试 Agent 复测。验收发现覆盖缺口则回到测试 Agent，补充测试先证明 RED，再进入实现循环。
