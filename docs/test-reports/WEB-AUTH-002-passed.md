# WEB-AUTH-002 独立复测报告

- 测试角色：测试 Agent
- 状态：`TEST_PASSED`
- 工作目录：`G:/job`
- 测试范围：WEB-AUTH-001、WEB-AUTH-002 Vitest
- 生产实现：未修改 `frontend/src`

## 环境

- `.nvmrc`：`20.19.0`
- Node.js：`v20.19.0`
- npm：`10.8.2`
- `npm ci`：成功
- Vitest：`4.1.11`
- Pinia：`4.0.3`
- Vue：`3.5.43`
- Vue Router：`5.3.1`

## 初始失败证据与 setup 修正

未修改测试的首次独立运行结果为 `14 passed, 2 failed`。两项失败是已确认的测试 setup 缺陷：路由测试未保存登录 Token，也未设置 `store.user`，却期望已登录访问 `/login`、`/register` 跳转 `/applications`。

依据 WEB-AUTH-002 公开契约，已登录路由必须显式建立 Token 和用户状态。因此仅在测试中补充登录 Token 与 `store.user`，未放宽断言；依据已追加至 [WEB-AUTH-002-red.md](G:/job/docs/test-reports/WEB-AUTH-002-red.md)。

## 复测命令与结果

```text
npx vitest run tests/test_token_storage.spec.ts tests/test_web_auth_002.spec.ts --reporter=dot
```

结果：

```text
Test Files  2 passed (2)
Tests       16 passed (16)
Duration    1.27s
```

验证通过：

- WEB-AUTH-001 token storage、Bearer、refresh 单次重试、并发队列、失败清理；
- Store user/initialized/loading、初始化 me、过期/刷新失败、初始化去重；
- logout 成功、HTTP 失败、网络错误均清理状态；
- 未登录保护路由 redirect 编码；
- 已登录 `/login`、`/register` 跳转 `/applications`。

## 结论

`TEST_PASSED`：WEB-AUTH-002 修正测试 setup 后，与 WEB-AUTH-001 全部 Vitest 通过。未修改 `frontend/src`。

黑盒声明：未读取或分析 `frontend/src` 生产实现代码。
