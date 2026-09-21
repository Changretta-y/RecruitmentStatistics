# WEB-AUTH-002 RED 报告

- 测试角色：测试 Agent
- 状态：RED_CONFIRMED
- 工作目录：G:/job
- 测试文件：G:/job/frontend/tests/test_web_auth_002.spec.ts
- 生产实现：未读取或修改 frontend/src

## 环境

- .nvmrc：20.19.0
- Node.js：v20.19.0
- npm：10.8.2
- npm ci：成功
- Vitest：4.1.11
- Pinia：4.0.3
- Vue：3.5.43
- Vue Router：5.3.1
- 环境缺口：无

## 覆盖范围

- Store user、initialized、loading 状态；
- 初始化读取 token、调用 me、过期/刷新失败清理；
- 并发初始化防重复认证请求；
- logout 成功、HTTP 失败、网络错误均清理 token/user；
- 未登录保护路由跳转 /login?redirect=<原地址>；
- 已登录访问 /login、/register 跳转 /applications。

## RED 命令与结果

```text
npx vitest run tests/test_web_auth_002.spec.ts --reporter=dot
```

结果：

```text
Test Files  1 failed (1)
Tests       9 failed (9)
Duration    1.09s
```

失败证据：

```text
Cannot find module '/src/stores/auth'
Cannot find module '/src/router'
```

Pinia、Vue、Vue Router 已可解析，测试正常收集并运行；失败指向当前实现尚未提供公开 auth store 和 router 模块，不是依赖安装、Node/npm、Vitest、语法或测试夹具错误。

## 结论

RED_CONFIRMED：WEB-AUTH-002 Store/路由认证行为尚未落地，已形成真实 RED 证据。未修改 frontend/src。

黑盒声明：未读取或分析 frontend/src 生产实现代码。


## READY_FOR_TEST 初始证据（未改测试）

命令：

npx vitest run tests/test_token_storage.spec.ts tests/test_web_auth_002.spec.ts --reporter=dot

结果：14 passed, 2 failed。失败仅为“已登录访问 /login、/register 跳 /applications”两项；测试当时没有写入登录 Token，也没有设置 auth store.user，实际仍处于未登录态，因此该失败属于测试 setup，不是实现失败。根据公开契约，已登录路由测试必须显式建立 Token 和 user；本轮仅补充该 setup，不放宽断言。
