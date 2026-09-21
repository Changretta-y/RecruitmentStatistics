# WEB-APP-003 RED 测试报告

## 状态

RED_CONFIRMED

## 测试角色与边界

- 测试角色：测试 Agent
- 新增测试：`frontend/tests/test_web_app_003.spec.ts`
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
  npx vitest run tests/test_web_app_003.spec.ts --reporter=dot
  ```

## 结果与失败证据

Vitest 正常启动并转换测试文件，但加载待测公开组件时失败：

```text
Error: Failed to resolve import "../src/components/ApplicationForm.vue"
from "tests/test_web_app_003.spec.ts"
Does the file exist?

Test Files  1 failed (1)
Tests       no tests
Exit code   1
```

该失败稳定指向 WEB-APP-003 要求的公开 `ApplicationForm.vue` 组件尚未提供。测试依赖、Node/npm、Vitest 和测试语法均已正常运行，不属于环境阻塞或夹具错误。

## 覆盖的公开契约

新增黑盒组件测试已覆盖：

- 新增模式默认字段和完整字段展示；
- 编辑模式回填副本且不修改原始列表行；
- 六阶段时间设置、修改、清空，ISO 与 `null` 传输；
- 公司/岗位必填、状态和时间格式校验；
- 提交 loading 与重复提交阻止；
- 新增 POST 语义；
- 编辑 PATCH 只提交变化字段；
- 成功后的关闭/清理/刷新第 1 页事件；
- 后端字段错误映射、失败保留输入；
- 未保存关闭确认。

## 结论

确认真实 RED，交由实现阶段实现公开表单组件后再独立复测。本阶段未修改 `frontend/src`，也未把依赖缺失冒充为 RED。
