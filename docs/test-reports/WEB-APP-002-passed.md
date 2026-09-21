# WEB-APP-002 独立复测报告

## 状态

TEST_PASSED

## 环境

- 工作目录：`G:\job\frontend`
- Node：20.19.0
- npm：10.8.2
- Vitest：4.1.11
- `npm ci`：成功（仅有依赖树 engine warning）

## 执行命令

```text
nvm use 20.19.0
npm ci
npx vitest run tests/test_web_app_002.spec.ts tests/test_token_storage.spec.ts tests/test_web_auth_002.spec.ts tests/test_web_auth_003.spec.ts tests/test_web_app_001.spec.ts --reporter=dot
```

## 结果

```text
Test Files  5 passed (5)
Tests       42 passed (42)
Exit code   0
```

WEB-APP-002 专项与 WEB-AUTH-001/002/003、WEB-APP-001 回归全部通过。

## WEB-APP-002 覆盖证据

- 当前 query/分页请求及公司、岗位、状态、六阶段时间、更新时间展示；
- 搜索、status、stage、时间起止、ordering 参数进入列表请求；
- 修改筛选/排序/page size 时页码重置为 1；
- 翻页保留既有查询条件；
- URL query 初始恢复及浏览器后退恢复；
- 顶部当前用户、退出和新增入口；
- 初次空列表、无结果、网络错误、401 状态及查询保留；
- 并发搜索只接受最新响应。

此前 jsdom 不支持的 `:has-text()` 已替换为标准 CSS 定位和基于公开按钮文本的 Vue Test Utils 查找，修正后的测试选择器已随本轮通过验证。

## 回归说明

WEB-AUTH-003 输出了 Vue Router 空路径 warning，但无测试失败、未处理错误或环境阻塞。

本轮未修改 `frontend/src` 生产实现，仅保留测试选择器/夹具修正并写入测试报告。
