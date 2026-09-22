# Agent 协作入口

本项目以用户提出的新需求或 bug 作为默认入口。普通对话负责理解问题和补齐必要信息；正式任务启动后，再进入角色隔离的 TDD 流程：项目管理 Agent 拆解与验收，测试 Agent 先写测试并独立复测，功能实现 Agent 只写实现。一个 Agent 在一个正式任务中只承担一个角色。

## 默认对话入口

1. 用户可以直接提出需求、bug、疑问或期望结果，无需提供任务编号或指定角色。
2. 在普通对话阶段，先理解目标、现状、影响范围和可验证的完成条件；信息足以启动任务时，将请求交给项目管理 Agent 拆解。
3. 需求澄清、问题复现信息收集和方案讨论仍属于普通对话，不受任务编号、角色分派和目录所有权门禁限制。
4. 未启动正式任务前，不进入测试编写、生产实现、复测或验收阶段。

完成标准：请求已被清楚理解；若需要执行项目改动，已具备交给项目管理 Agent 启动正式任务所需的信息。

## 启动正式任务

1. 项目管理 Agent 根据已确认的需求或 bug 创建任务、分配任务编号，并为每个执行 Agent 指定单一角色。
2. 被分派的 Agent 确认任务编号、角色、允许修改的目录、当前状态及本阶段完成条件；信息不完整时向项目管理 Agent 反馈。
3. 阅读 [系统设计](校招进度管理系统-详细设计方案.md) 中与当前任务有关的需求和公开契约。
4. **环境**：当任务涉及安装依赖、切换运行时、执行脚本、测试或构建时，先读取 [uv 与 nvm 环境规范](docs/agents/environment.md)。
5. 按角色读取且只读取对应说明：
   - **项目管理**：当任务涉及需求拆解、调度或验收时，读取 [项目管理 Agent](docs/agents/project-manager.md)。
   - **测试编写**：当任务涉及测试设计、RED 证明、复测或测试报告时，读取 [测试 Agent](docs/agents/test-agent.md)。
   - **功能实现**：当任务涉及前后端实现、迁移或实现修复时，读取 [实现 Agent](docs/agents/implementation-agent.md)。
6. 当任务发生交接、失败回流或状态变更时，读取 [TDD 工作流](docs/agents/workflow.md)。
7. 当需要产出任务单、测试报告、实现说明或验收记录时，读取 [交付模板](docs/agents/templates.md)。

完成标准：任务编号和角色已分配，输入文档、允许修改的目录、当前状态及本阶段完成条件均已明确。

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
