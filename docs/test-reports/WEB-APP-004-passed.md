# WEB-APP-004 独立复测报告

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
npx vitest run tests/test_web_app_004.spec.ts tests/test_web_app_003.spec.ts tests/test_web_app_002.spec.ts tests/test_web_app_001.spec.ts tests/test_token_storage.spec.ts tests/test_web_auth_002.spec.ts tests/test_web_auth_003.spec.ts --reporter=dot
```

## 结果

```text
Test Files  7 passed (7)
Tests       59 passed (59)
Exit code   0
```

WEB-APP-004 专项及 WEB-APP-001~003、WEB-AUTH-001~003 回归全部通过。

## WEB-APP-004 覆盖证据

- 删除对话框展示公司和岗位；
- 取消删除不发请求；
- 确认删除发送正确记录 ID、刷新列表并显示成功提示；
- 当前页最后一条删除后页码回退到第 1 页；
- 404、403、500 和网络错误展示可理解提示，网络失败可重试；
- 空数据提供新增入口，无结果提供重置筛选；
- 错误提示不泄露 Token、密码或堆栈；
- 删除操作可通过键盘触发并保持公开按钮语义。

## 回归说明

WEB-AUTH-003 输出 Vue Router 空路径 warning，但无测试失败、未处理错误或环境阻塞。

本轮未修改 `frontend/src`，仅执行测试并写入本报告。
