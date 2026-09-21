# WEB-APP-001 独立复测报告

## 状态

TEST_PASSED

## 环境

- 工作目录：`G:\job\frontend`
- Node：20.19.0
- npm：10.8.2
- Vitest：4.1.11
- PostgreSQL/API：本专项为前端黑盒测试，不需要额外数据库操作
- `npm ci`：成功

## 执行命令

```text
nvm use 20.19.0
npm ci
npx vitest run tests/test_web_app_001.spec.ts tests/test_token_storage.spec.ts tests/test_web_auth_002.spec.ts tests/test_web_auth_003.spec.ts --reporter=dot
```

## 结果

```text
Test Files  4 passed (4)
Tests       35 passed (35)
Exit code   0
```

WEB-APP-001 专项及 WEB-AUTH-001/002/003 回归全部通过。覆盖并验证：

- JobApplication 分页响应与 snake_case/camelCase 转换；
- null 与 ISO 时间无损传递；
- query 默认值、pageSize 白名单、非法 query 回退；
- 对象与 URL query 双向转换、空筛选省略、ordering 的 `-` 保留；
- 统一 HTTP 层调用、PATCH null 传递及错误类型；
- 既有 token storage、认证 store/router、登录注册组件回归。

测试输出包含 Vue Router 空路径 warning，但无测试失败或环境阻塞。未修改 `frontend/src` 生产实现。
