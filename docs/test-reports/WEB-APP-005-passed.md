# WEB-APP-005 独立复测报告

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 工作目录：`G:\job\frontend`
- 环境：Windows；Node.js 20.19.0（`.nvmrc`）；npm 10.8.2；Vitest 4.1.11
- 依赖同步：运行 `nvm use 20.19.0` 后确认 `nvm current`、`node --version` 均为 `v20.19.0`，执行 `npm ci` 成功。npm 对 `abbrev`、`nopt` 显示 engine warning；安装、Vitest 和定向测试均正常。
- 黑盒声明：通过现有表单测试观察公开 UI 和 API mock 请求；未读取或修改 `frontend/src/`，未修改测试断言。

## WEB-APP-005 专项与 WEB-APP-003 回归

```text
npm run test -- tests/test_web_app_005.spec.ts tests/test_web_app_003.spec.ts --reporter=dot --maxWorkers=1
```

结果：`Test Files 2 passed (2)`、`Tests 19 passed (19)`。单独运行时 WEB-APP-005 为 10/10、WEB-APP-003 为 9/9。使用单 worker 合跑可稳定通过；默认并行合跑曾使 WEB-APP-005 的单个耗时用例超过 Vitest 5 秒默认超时。

WEB-APP-005 通过证据覆盖六个独立时长输入、空值禁用、新开始时间默认 60 分钟、六阶段时长 POST 载荷、编辑回填各自真实值、只改开始时间保留自定义时长、清空开始时间时同步清空时长并提交 `null`、范围/类型错误阻止提交及字段错误定位、服务端字段错误映射、服务端/网络失败保留输入。WEB-APP-003 新增/编辑和未保存确认回归 9/9 通过。

## 全前端测试结果及边界

```text
npm run test -- --reporter=dot --maxWorkers=1
```

连续两次结果相同：`Test Files 2 failed | 12 passed (14)`、`Tests 3 failed | 99 passed (102)`。失败均来自既有 WEB-APP-002/004 测试：

- WEB-APP-002 URL 后退/前进后搜索框仍显示“新查询”，而非预期“示例”；退出后路由仍为 `/applications`，而非 `/login`。
- WEB-APP-004 点击重置筛选后 `query.search` 仍为“无结果”。

两项失败的独立运行也分别复现（WEB-APP-002：2 项失败、5 项通过；WEB-APP-004：1 项失败、7 项通过）。失败行为属于列表 URL/退出/筛选交互，不属于 WEB-APP-005 时长表单公开契约；本次定向专项与指定的 WEB-APP-003 相关回归均通过。更广范围测试未全绿的情况已如实记录，需由项目管理 Agent 决定是否另立或转交对应任务跟进。

## 结论与交接

WEB-APP-005 专项和任务指定的新增/编辑表单回归全部通过，状态建议更新为 `TEST_PASSED`。全量前端套件存在上述三项稳定的既有列表交互失败；未将其混同为时长表单失败，也未隐去结果。

- 通过 / 失败：专项及 WEB-APP-003 回归 `19 / 0`；全量前端 `99 / 3`。
- 稳定性：专项单 worker 连续/独立验证通过；全量前端在单 worker 下两次重现相同三项失败。
- 未覆盖风险：全量套件中的 WEB-APP-002 和 WEB-APP-004 失败仍待对应角色确认处理；未进行生产代码因果分析，遵守测试 Agent 黑盒边界。
