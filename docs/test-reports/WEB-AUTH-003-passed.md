# WEB-AUTH-003 独立复测报告

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 工作目录：`G:/job`
- 生产实现：未修改 `frontend/src`

## 环境

- `.nvmrc`：`20.19.0`
- Node.js：`v20.19.0`
- npm：`10.8.2`
- `npm ci`：成功
- Vitest：`4.1.11`
- Vue Test Utils、jsdom：已安装并锁定

## 组件专项

```text
npx vitest run tests/test_web_auth_003.spec.ts --reporter=dot
```

结果：

```text
Test Files  1 passed (1)
Tests       7 passed (7)
Duration    11.06s
```

覆盖通过：注册/登录字段校验、密码一致性、提交 loading/disabled、后端字段错误、注册成功不自动登录并跳登录、登录成功 Token/user 与 redirect、401 通用提示、网络/500 保留输入重试。

## WEB-AUTH-001/002 回归

```text
npx vitest run tests/test_token_storage.spec.ts tests/test_web_auth_002.spec.ts tests/test_web_auth_003.spec.ts --reporter=dot
```

结果：

```text
Test Files  3 passed (3)
Tests       23 passed (23)
Duration    2.25s
```

运行中出现 Vue Router 对测试初始空路径的提示 warning，但无失败，不影响断言或通过结果。

## 结论

`TEST_PASSED`：WEB-AUTH-003 专项及 WEB-AUTH-001/002 相关回归全部通过。未修改 `frontend/src`。

黑盒声明：未读取或分析 `frontend/src` 生产实现代码。
