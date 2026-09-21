# WEB-AUTH-001 RED 报告

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 工作目录：`G:/job`
- 测试文件：`G:/job/frontend/tests/test_token_storage.spec.ts`
- 生产实现：未读取或修改 `frontend/src`

## 前端测试环境

- `.nvmrc`：`20.19.0`
- `nvm use 20.19.0`：成功
- Node.js：`v20.19.0`
- npm：`10.8.2`
- `npm install --save-dev vitest`：成功，安装 Vitest `4.1.11`
- `npm ci`：成功
- `package.json` / `package-lock.json`：已加入测试依赖；测试脚本配置为 `vitest`

## 测试覆盖

公开黑盒测试覆盖：

- token-storage 统一保存、读取、清除及 `accessToken/refreshToken/expiresAt` 结构；
- 本地 7 天截止时间过期后自动清理；
- 受保护请求注入 `Authorization: Bearer <access>`；
- 401 单次 refresh、轮换 Token 和原请求单次重试；
- 并发 401 共用一个 refresh 任务并释放等待队列；
- refresh 接口自身不递归触发刷新；
- refresh 失败清除 Token 并拒绝所有等待请求。

## RED 命令与结果

```text
npx vitest run tests/test_token_storage.spec.ts --reporter=dot
```

结果：

```text
Vitest v4.1.11
7 failed, 0 passed
Test Files  1 failed (1)
Tests       7 failed (7)
```

失败原因稳定指向真实缺失行为：

```text
Cannot find module '/src/utils/token-storage'
imported from G:/job/frontend/tests/test_token_storage.spec.ts
```

所有 7 项测试均在导入公开 token-storage 模块时失败，当前公开契约模块尚不存在；这不是 Vitest、Node/npm、依赖安装、语法或测试夹具错误。Axios client 相关断言已包含在同一黑盒测试文件中，待 token-storage 公开模块落地后继续暴露并验证其行为。

## 结论

`RED_CONFIRMED`：WEB-AUTH-001 的统一 Token 存储模块及其依赖的自动刷新行为尚未落地，已形成真实 RED 证据。未修改 `frontend/src`。
