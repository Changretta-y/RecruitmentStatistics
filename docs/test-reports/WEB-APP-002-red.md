# WEB-APP-002 RED 测试报告

## 状态

RED_CONFIRMED

## 测试角色与边界

- 测试角色：测试 Agent
- 仅新增 `frontend/tests/test_web_app_002.spec.ts` 与本报告
- 未读取或修改 `frontend/src` 生产实现

## 环境与命令

- 工作目录：`G:\job\frontend`
- Node：20.19.0
- npm：10.8.2
- Vitest：4.1.11
- `npm ci`：成功
- 执行命令：

  ```text
  nvm use 20.19.0
  npm ci
  npx vitest run tests/test_web_app_002.spec.ts --reporter=dot
  ```

## 结果与失败证据

Vitest 正常启动并完成测试文件转换，但导入公开组件时失败：

```text
Error: Failed to resolve import "../src/views/ApplicationsView.vue"
from "tests/test_web_app_002.spec.ts"
Does the file exist?

Test Files  1 failed (1)
Tests       no tests
Exit code   1
```

失败稳定地指向 WEB-APP-002 要求的 `ApplicationsView.vue` 公开组件尚未提供。由于组件模块不存在，7 个黑盒行为用例尚未进入执行阶段；这不是 npm/Vitest 依赖缺失、命令失败、测试语法错误或测试夹具错误。

## 覆盖的公开契约

新增测试已编写并覆盖以下行为：

- 使用当前 query/分页请求并展示公司、岗位、状态、六阶段时间和更新时间；
- 搜索、状态/阶段/时间筛选、ordering、page size 与页码重置；
- 翻页保留既有筛选条件；
- URL query 初始恢复及浏览器前进/后退恢复；
- 当前用户、退出和新增入口；
- 首次空列表、筛选无结果、网络错误、401 状态及查询保留；
- 并发搜索只接受最新响应。

## 结论

依赖和测试运行环境已确认正常，失败原因是待测生产组件缺失，确认真实 RED，交由实现阶段继续实现。未扩展生产代码，也未修改 `frontend/src`。
