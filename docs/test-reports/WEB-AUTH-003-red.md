# WEB-AUTH-003 RED 报告

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 工作目录：`G:/job`
- 测试文件：`G:/job/frontend/tests/test_web_auth_003.spec.ts`
- 生产实现：未读取或修改 `frontend/src`

## 环境

- `.nvmrc`：`20.19.0`
- Node.js：`v20.19.0`
- npm：`10.8.2`
- `npm ci`：成功
- Vitest：`4.1.11`
- `@vue/test-utils`：已安装为测试依赖
- `jsdom`：已安装为测试依赖
- Vue/Pinia/Router：已安装并锁定
- 环境缺口：无

## 覆盖范围

- RegisterView 用户名/密码/确认密码字段校验和密码一致性；
- 注册提交 loading/按钮禁用、后端字段错误映射；
- 注册成功提示、跳转登录且不自动登录；
- LoginView 不完整凭据校验、401 通用提示；
- 网络/500 错误保留输入并支持重试；
- 登录提交 loading/按钮禁用、Token/user 成功态及 applications/redirect 跳转。

## RED 命令与结果

```text
npx vitest run tests/test_web_auth_003.spec.ts --reporter=dot
```

结果：

```text
Failed Suites  1
Tests          no tests
```

失败证据：

```text
Failed to resolve import "../src/views/RegisterView.vue"
from tests/test_web_auth_003.spec.ts
Does the file exist? false
```

Vitest 与 jsdom 已正常启动，失败发生在解析公开组件模块时；不是 npm 网络、Node/npm、Vitest、jsdom、测试语法或夹具错误。任务要求的 RegisterView/LoginView 生产组件尚未提供，因此当前无法收集并执行组件断言。

## 结论

`RED_CONFIRMED`：WEB-AUTH-003 所需公开 LoginView/RegisterView 尚未落地，已形成真实 RED 证据。未修改 `frontend/src`。

黑盒声明：未读取或分析 `frontend/src` 生产实现代码。
