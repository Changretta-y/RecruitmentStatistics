# WEB-APP-004 RED 测试报告

## 状态

RED_CONFIRMED

## 测试角色与边界

- 测试角色：测试 Agent
- 新增测试：`frontend/tests/test_web_app_004.spec.ts`
- 未读取或修改 `frontend/src` 生产实现

## 环境与命令

- 工作目录：`G:\job\frontend`
- Node：20.19.0
- npm：10.8.2
- Vitest：4.1.11
- `npm ci`：成功（仅有依赖树 engine warning）
- 执行命令：

  ```text
  nvm use 20.19.0
  npm ci
  npx vitest run tests/test_web_app_004.spec.ts --reporter=dot
  ```

## 结果

```text
Test Files  1 failed (1)
Tests       7 failed | 1 passed (8)
Exit code   1
```

## 失败证据

Vitest 正常收集并执行组件测试。7 个失败均稳定发生在公开删除操作定位阶段：

```text
AssertionError: a public delete action is required: expected undefined to be truthy
```

测试已经能够挂载 `ApplicationsView` 并验证空数据入口；但带有公开记录的列表中没有可观察的删除按钮/键盘删除操作，因此删除对话框、取消、确认 DELETE、刷新、分页回退及 DELETE 错误处理用例无法继续验证。这是 WEB-APP-004 所要求行为缺失，不是依赖、Vitest、语法或测试夹具错误。

## 覆盖的公开契约

新增黑盒测试覆盖：

- 删除对话框展示公司和岗位；
- 取消不发请求；
- 键盘可操作；
- 确认 DELETE 正确 ID、刷新当前页和成功提示；
- 当前页最后一条删除时回退到上一页；
- 404/403/500/网络错误的安全提示与重试；
- 空数据新增入口；
- 无结果重置筛选；
- 错误消息不泄露 Token、密码或堆栈。

## 通过项

- 空数据展示新增入口的用例通过。

## 结论

确认真实 RED，交由实现阶段补齐公开删除交互后再独立复测。本阶段未修改 `frontend/src`，也未将环境问题冒充为 RED。
