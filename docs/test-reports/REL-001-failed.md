# REL-001 TEST_FAILED

- 测试角色：测试 Agent
- 状态：`TEST_FAILED`
- 工作目录：`G:\job`
- 环境：Windows；nvm current `v20.19.0`；Node.js `v20.19.0`；npm `10.8.2`；Vitest `4.1.11`
- 修改范围：仅新增 `frontend/tests/test_rel_001_auth_store.spec.ts`；未修改生产源代码、coverage 配置或依赖配置。
- 命令：`npm run test:coverage`
- 新增测试定向命令：`npx vitest run tests/test_rel_001_auth_store.spec.ts --reporter=dot`

## 结果

新增测试定向复跑两次均为：`4 passed, 3 failed`（7 tests）。失败稳定，均为 logout 导航断言：Store 清理 user/token 已完成，但 mock router 的 `push("/login")` 没有被调用。

完整 coverage 基线（新增测试前）真实结果：`59 passed`，全局 branches `73.51%`，未达到 `80%`；`src/stores/auth.ts` branches `60%`，未达到 Store 分支门禁。加入新增测试后，`npm run test:coverage` 为 `63 passed, 3 failed`，因测试失败未形成可接受的通过 coverage 门禁结果。

## 覆盖的公开行为

- `initialize()` 无 token：不调用 `me`，完成 initialized/loading 状态。
- `initialize()` 调用 `me` 成功：恢复 user。
- `initialize()` 调用 `me` 失败：清理 session，仍完成初始化。
- `login(credentials)`：向登录 API 传递 credentials，并持久化 access/refresh/user session。
- logout API 成功与失败：均清理 user/token。
- logout 导航异常：导航失败不应让 logout Promise 拒绝。
- 现有 `test_token_storage.spec.ts` 保留并回归 token refresh 成功、并发 401、refresh 自身 401、refresh 失败清理等边界。

## 失败证据

失败用例：

- `clears user and token state after a successful logout`
- `clears user and token state when the logout API fails`
- `does not reject logout when navigation to login fails`

三项实际失败均为：`expected vi.fn() to be called with arguments: [ '/login' ]`，`Number of calls: 0`。清理状态相关断言在同一用例中通过。

## 回归结果

- 原有前端测试：`59 passed`。
- 加入本次测试后：`63 passed, 3 failed`。
- 覆盖率门禁：未通过；不能据此宣称 REL-001 通过。

## 后续交接

请实现 Agent 依据公开契约检查 logout 成功、失败和导航容错行为；修复后由测试 Agent 使用同一新增测试与 `npm run test:coverage` 独立复测。测试 Agent 未修改生产实现，也未以放宽断言方式绕过失败。

## 黑盒声明

测试依据任务单、系统设计和公开 API/Store 行为编写；未读取或分析 `frontend/src` 生产实现代码。
